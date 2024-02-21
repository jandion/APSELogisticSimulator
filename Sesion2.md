
En esta sesión vamos a trabajar con los datos que genera el simulador. Por un lado, tendremos los datos de los planes que se han ejecutado, y por otro lado, los datos de los eventos que se han producido durante la ejecución de los planes. Empezaremos realizando una exploración de los datos para familiarizarnos con el dominio y finalmente transformaremos los datos en bruto a un formato apto para entrenar modelos que nos permitan predecir el tiempo de viaje de los camiones o de entrega de los paquetes. Todas estas tareas se pueden realizar en un cuaderno de código como Jupyter Notebook.

Utilizaremos 2 archivos de datos que contienen la información de los planes y de los eventos que se han producido durante la ejecución de estos planes. El primer archivo es 'plans.jsonlines', que contiene un conjunto de escenarios que ya han sido simulados. Cada uno de ellos está representado por el json que obtenemos al llamar a /createPlan. El segundo archivo es 'simulation.jsonlines', que contiene los eventos que se han producido durante la ejecución de los planes. La extensión '.jsonlines' indica que cada línea del archivo es un json independiente, en pandas se puede leer con la función `pd.read_json` con el parámetro `lines=True`.

## Objetivos

- Explorar los datos de salida del simulador
- Transformar los datos en bruto a un formato apto para entrenar modelos de ML
- Entrenar modelos de ML para predecir el tiempo de viaje de los camiones o de entrega de los paquetes
## Paso 1: Exploración de los datos

En primer lugar vamos a cargar los datos y a realizar un EDA para familiarizarnos con el dominio. Para cargar los datos podemos usar un código similar al siguiente:

```python

import pandas as pd

...

df = pd.read_json('[RUTA AL ARCHIVO .jsonlines]', lines=True)

```

Una vez cargados los datos, tendremos que hacer una breve exploración de los mismos. Algunas preguntas que nos podemos hacer son:

- ¿Cuántas filas y columnas tiene cada dataset?
- ¿Cuántas simulaciones se han realizado? ¿Cuántos eventos se han producido en total? ¿Cuántos planes se han ejecutado?
- ¿Cuántos eventos se han producido por tipo?
- ¿Cómo se representan los tiempos en los datos?
- ¿Cuánto tiempo se tarda en entregar un paquete?

> [!TIP]

> Para responder a la última pregunta, podemos utilizar el dataframe con los eventos, filtrarlo para quedarnos solo con los eventos "Truck ended delivering" y "Truck started delivering", y calcular la diferencia entre los tiempos de estos eventos. Para ello, podemos ordenar el dataframe por simulación, camión y tiempo, y después aplicar la función `diff` de pandas para calcular la diferencia entre los tiempos de los eventos.

Una conclusión importante que deberíamos sacar de esta primera exploración es los planes se organizan de una manera poco habitual. En lugar de ser una tabla regular, los planes contienen objetos anidados que representan las rutas de los camiones y los paquetes que se han entregado.
## Paso 2: Transformación de los datos

En este paso tendremos dos objetivos. Por un lado, tendremos que combinar la información de los planes y los eventos en un único dataset. Por otro lado, habrá que desanidar los objetos que aparecen en los planes para generar un dataset tabular. El resultado de este paso serán dos datasets: uno con la información de los tiempos de viaje de los camiones y otro con la información de los tiempos de entrega de los paquetes.
### Desanidar los objetos de los planes

Utilizando pandas, una posible función para desanidar los objetos contenidos en los planes es `explode` (https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.explode.html).

```python  

# Suponiendo que el dataframe con los planes se llama df_plans

df_plans.join(df_plans.trucks.explode().apply(pd.Series), lsuffix='_sim').reset_index(drop=True)

```

Ahora deberíamos repetir ese proceso con la columna 'route'.

### Combinar la información de los planes y los eventos

Para combinar la información de los planes y los eventos, podemos utilizar nuevamente la función `join`. Esto funcionará si ambos datasets tienen el mismo número de filas y están ordenados de la misma manera. Para lograr esto, tendremos que transformar el dataset de eventos para que tenga una fila por cada viaje de camión y que incluya una columna con el tiempo de viaje.
### Resultado

A continuación se muestra un ejemplo de que columnas (al menos) deberían tener los datasets resultantes.

#### Dataset de tiempos de viaje de los camiones

| truck | estimated_travel_time | actual_travel_time |
| ---- | ---- | ---- |
#### Dataset de tiempos de entrega de los paquetes

| truck | estimated_delivery_time | actual_delivery_time |
|-------|-------------------------|----------------------|
## Paso 3: Entrenar modelos de ML


En este último paso, entrenaremos dos modelos de predicción. Uno para predecir el tiempo de viaje de los camiones y otro para predecir el tiempo de entrega de los paquetes. Este paso es libre, y se puede utilizar cualquier biblioteca o algoritmo que se considere oportuno. El modelo tendrá que evaluarse utilizando alguna métrica adecuada. Finalmente, deberemos guardar cada modelo (y cualquier paso de preprocesamiento que sea necesario) para poder utilizarlo en la siguiente sesión. Por simplicidad, guardaremos los modelos en formato pickle:

  
```python

import pickle

...

with open('model.pkl', 'wb') as f:

    pickle.dump(model, f)

```

Este paso implica decidir que variables se utilizarán como entrada del modelo. En el paso anterior hemos generado dos datasets que contienen muchas variables y no todas ellas tendrán una influencia real en la predicción. Habrá que descartar aquellas que no sean importantes o que estén altamente correladas con otras que ya hayamos seleccionado. Por ejemplo, cabría esperar que el tiempo de viaje en la simulación esté relacionado con el tiempo de viaje que se estimó en el plan, pero no esté relacionado con el id de la simulación.

A continuación, se listan unas cuantas ideas de variables que podrían formar parte del vector. En esta lista, hay algunas de las variables que influyen de verdad en el comportamiento del camión y también otras que no guardan relación.

* Tiempo de viaje acumulado durante la ruta: Cuanto tiempo de viaje lleva el camión en esta simulación.

* Carga del camión: Porcentaje de ocupación del camión, es decir número de paquetes que transporta dividido por la capacidad máxima.

* La localización de destino

* El número de localizaciones diferentes visitadas en la ruta

* El número de localizaciones planificadas en la ruta

* El tiempo de viaje estimado para el trayecto actual

* El identificador del paquete que se está entregando

* El número de paquetes que se entregan en la localización actual

* El número de letras distintas en el id de simulación

* El identificador del camión

## Entrega

Describir que variables se han utilizado para entrenar los modelos, que algoritmo se ha seleccionado y que métricas se han utilizado para evaluarlos.