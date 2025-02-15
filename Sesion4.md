En esta sesión del bloque de la asignatura, utilizaremos los modelos de predicción de la sesión anterior conectados a la salida de eventos del simulador. Las predicciones se tendrán que ejecutar en tiempo real según lleguen los mensajes por la cola Kafka, y los resultados se enviarán nuevamente a Kafka.

Para hacer estas predicciones en tiempo real, habrá que mantener un vector, por cada camión y simulación, con las variables de entrada de los modelos. Según lleguen nuevos eventos, se actualizará el vector correspondiente y dependiendo del tipo de evento, se calculará una predicción.

Para hacer estas predicciones no podemos usar un notebook de Python, ya que tendremos que esperar de forma indefinida a que lleguen mensajes y esto no funcionaría ejecutando una celda. En su lugar se utilizará un programa en Python normal, es decir un archivo `.py` que ejecutaremos desde la terminal. Llamaremos a este archivo `prediccionesOnline.py`,  en la carpeta `data/prediccion` hay una versión inicial del mismo.  A continuación, se presenta un seudocódigo del programa que tendremos que escribir.

```python
# Cargar los modelos entrenados y conectar con kafka
vectores = {}


for evento in kafka.topic:
  # Si no habíamos recibido ningún evento con este simulationId y truck_id, obtenemos su plan desde la base de datos
  if not (evento.simulationId,evento.truck_id) in vectores:
    obtenerPlan(evento)

  # Actualizamos el vector correspondiente según el vector de características de cada uno de los modelos
  actualizarVectores(evento)
  
  # Si el evento es de comienzo de viaje, hacemos una predicción
  if (evento.eventType in ["Truck departed", "Truck departed to depot"]):
    prediccion = prediccionDeTiempoDeViaje(evento)
    escribirEnKafka(prediccion)
  # Si el evento es de comienzo de entrega, hacemos una predicción
  elif (evento.eventType == "Truck started delivering"):
    prediccion = prediccionDeTiempoDeEntrega(evento)
    escribirEnKafka(prediccion)
  # Si el evento es final de ruta, borramos el vector para liberar memoria
  elif (evento.eventType == "Truck ended route"):
    del(vectores[(evento.simulationId,evento.truckId)])
```

Antes de empezar, hay que actualizar la carpeta de trabajo con la última versión del repositorio de GitHub (https://github.com/jandion/APSELogisticSimulator). En los siguientes pasos, rellenaremos los métodos que aparecen nombrados en el código anterior. Es recomendable añadir mensajes de trazas al cuerpo de los métodos, para poder comprobar que todo funciona como debe.

El diccionario `vectores` se utilizará como un almacén dónde guardemos toda la información relacionada con un camión. Como clave del diccionario utilizamos la tupla (simulationId,truckId), para poder identificar un reparto completo de un camión. Como valor, tendremos otro diccionario en el que habrá una clave `vector`, en la que almacenaremos el vector que se le pasará a los modelos de predicción. 

## Paso 0. Los modelos de predicción

Idealmente, se empezará esta sesión con unos modelos de predicción previamente entrenados. Si no es así,  podemos utilizar el notebook `data/model/model.ipynb` . Con este cuaderno se entrenan los dos modelos que necesitamos para hacer las predicciones. Son versiones muy simples, una regresión lineal que tiene como entrada una única variable.

 - El modelo de predicción de tiempos de viaje dependerá únicamente de la estimación que se hace en el plan de entrega
 - El modelo de predicción de tiempos de entrega, dependerá únicamente del camión que realice la entrega

Al ejecutar el notebook, se crearán 3 archivos `.pkl`
- `travelModel.pkl` con el modelo de predicción de tiempos de viaje
- `deliveryModel.pkl` con el modelo de predicción de tiempos de entrega
- `le.pkl` con el `LabelEncoder utilizado para codificar el camión en el modelo de los tiempos de entrega

Si hemos entrenados los modelos de alguna otra manera, podemos guardarlos en pickle para utilizarlos después en el programa de predicción.

```python
import pickle

# Código para entrenar el modelo

# Guardar modelo
with open('[nombre del archivo].pkl', 'wb') as f:
    pickle.dump(modelo, f)
```

De la misma manera, podemos guardar cualquier dependencia que necesitemos para crear los vectores de entrada del modelo (LabelEncoder, StandardScaler, etc).

Si queremos leer alguno de los modelos que hemos guardado en pickle, usaremos este código:
```python
with open('[nombre del archivo].pkl', 'rb') as f:
    modelo = pickle.load(f)
```

## Paso 1. Leer mensajes de las colas de Kafka

Para leer los mensajes de Kafka, se utiliza un Consumidor. Los consumidores son programas que leen mensajes de los canales de Kafka. En nuestro caso, se leerán todos los eventos generados por el simulador, que se envían por el canal, o topic, `simulation`. Los eventos llegan como strings, debemos convertirlos en diccionarios para trabajar con ellos.


```python
# Conectamos con el servidor de Kafka
client = pykafka.KafkaClient(hosts="localhost:9093")
# Elegimos el topic con el que queremos trabajar
topic = client.topics['simulation']

# ...

# Creamos el consumidor
consumer = topic.get_simple_consumer( consumer_group='prediccionOnline',
    reset_offset_on_start=True,
    auto_offset_reset=OffsetType.LATEST,
    auto_commit_enable=True,
    auto_commit_interval_ms=1000)

# Procesamos los mensajes segun van llegando
for evento in consumer:
  # Convertimos los mensajes en diccionarios
  evento = json.loads(evento.value.decode('utf-8'))
```



## Paso 2. Leer de la base de datos

Cada vez que se reciba un evento que corresponda con alguna simulación y camión que no se hubiera visto antes, se consultará el plan de entregas que se había estimado. Estos planes, además de devolverse como respuesta cuando se hace una petición POST a `/simulateScenario`, también se guardan en MongoDB, en la colección `simulations`. 

Esta consulta debemos hacerla en el método `obtenerPlan(evento)` 

```python
# conectar a mongo
client = pymongo.MongoClient("mongodb://localhost:27017/")
db = client["simulator"]
col = db["plans"]
# Obtener el plan de la simulación
plan = col.find_one({"simulationId": evento["simulationId"]})

# Buscamos en plan["trucks"] el camión con truckId = evento.truckId
camion = list(filter(lambda truck: truck["truck_id"] == evento["truckId"], plan["trucks"]))[0]

# En este diccionario guardaremos toda la información del plan que sea necesaria para realizar las predicciones 
# ADAPTAR SEGUN EL VECTOR DE ENTRADA DEL MODELO DE PREDICCIÓN
vector = {
    "tiemposEstimados": [ r["duration"] for r in camion["route"] ],
    "vector": np.array([])
}
# Añadir la información del camión al diccionario de vectores
vectores[(evento["simulationId"],evento["truckId"])] = vector

# Cerrar la conexión
client.close()
```



## Paso 3. Procesar los eventos

Según lleguen los eventos de la simulación, deberemos ir actualizando la información que tenemos guardada sobre los camiones. Dependiendo del tipo de evento, la actualización que se haga será diferente. En el diccionario con la información del camión, que guardamos en `vectores`, tenemos el campo `vector`, que será la entrada del modelo. En esta parte del código debemos actualizar el valor de ese campo y dejarlo preparado para usarlo en los métodos de predicción.

Este código lo incluiremos en el método `actualizarVectores(evento)`
```python
# Si el evento es de comienzo de viaje, añadimos el tiempo estimado de viaje al vector
if (evento["eventType"] in ["Truck departed", "Truck departed to depot"]):
  vectores[(evento["simulationId"],evento["truckId"])]["vector"] = np.array(vectores[(evento["simulationId"],evento["truckId"])]["tiemposEstimados"].pop(0))

# Si el evento es de comienzo de entrega, añadimos el id del camión al vector
elif (evento["eventType"] == "Truck started delivering"):
  vectores[(evento["simulationId"],evento["truckId"])]["vector"] = np.array(evento["truckId"])
```


## Paso 4. Hacer predicciones

Si el evento que estamos procesando es de inicio de un trayecto o de comienzo de una entrega, realizaremos una predicción con el modelo correspondiente.

Para el caso de predicción de tiempo de viaje, rellenaremos el método `prediccionDeTiempoDeViaje(evento)`:

```python
vector = vectores[(evento["simulationId"],evento["truckId"])]["vector"].reshape(-1, 1)
prediccion = modelo_tiempo_viaje.predict(vector)[0]
return # LA PREDICCIÓN Y LO QUE SEA NECESARIO PARA SABER QUE ES SOBRE UN TIEMPO DE VIAJE
```
  
Para el caso de predicción de tiempo de viaje, rellenaremos el método `prediccionDeTiempoDeEntrega(evento)`:

```python
vector = vectores[(evento["simulationId"],evento["truckId"])]["vector"].ravel()
# Codificar el id del camión
vector = labelEncoder.transform(vector)
prediccion = modelo_tiempo_entrega.predict(vector.reshape(-1, 1) )[0]

return # LA PREDICCIÓN Y LO QUE SEA NECESARIO PARA SABER QUE ES SOBRE UN TIEMPO DE ENTREGA
```

## Paso 5. Escribir mensajes en Kafka

Si para recibir mensajes de Kafka se utilizan programas llamados Consumidores, para escribir mensajes se utilizan Productores. Los productores pueden escribir mensajes a diferentes topics y con distintos formatos. En este caso, escribiremos mensajes en texto plano, codificados como objetos JSON, el formato exacto queda a la elección de cada uno. Este código lo pondremos en el método 

```python
# Conectamos con el topic de predicciones
topic = client.topics['predictions']

# Creamos el mensaje, que debería incluir el tipo de prediccion
mensaje = "" # DECIDIR EL FORMATO DE LOS MENSAJES CON LAS PREDICCIONES

# Enviamos el mensaje
with topic.get_sync_producer() as producer:
  producer.produce(mensaje.encode('utf-8'))
```


## Paso 6. Comprobar el resultado

Primero debemos ejecutar el programa que acabamos de escribir, para ello basta con ejecutar el archivo desde terminal con `python prediccionesOnline.py` . Después, ejecutaremos una simulación, haciendo una petición POST a `http://localhost:7500/simulateScenario` . Inmediatamente empezará a ejecutarse la simulación y deberíamos ver los mensajes en la terminal en la que se ejecutó el programa de predicción. Adicionalmente, se puede comprobar en la interfaz gráfica de Kafka, que se ha creado un nuevo canal/topic `predictions` y se están recibiendo las predicciones.

## Paso Extra. Visualizar las posiciones GPS

Se proporciona un servidor Flask que podemos utilizar para ver las posiciones de los camiones en tiempo real. Para ejecutarlo simplemente hay que ejecutar el archivo `visualizador/app.py` y abrir la web `http://localhost:5005`

## Paso Extra. Comprobar el error de las predicciones

De forma opcional, podemos intentar comprobar como de acertadas van siendo las predicciones de cada modelo. Podemos guardar las predicciones que se hagan, y cuando llegue el evento correspondiente comprobar el tiempo transcurrido y ver si coincide con lo que se predijo.

## Entrega

Una captura de los mensajes con las predicciones enviados a Kafka
