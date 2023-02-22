import pickle
import pymongo
import pykafka
import json
import numpy as np
from pykafka.common import OffsetType
from collections import namedtuple

########################################################
# Carga de modelos y labelEncoder y conexión con Kafka #
########################################################

# Cargamos los modelos y el labelEncoder
with open('data/prediccionOnline/travelModel.pkl', 'rb') as f:
    modelo_tiempo_viaje = pickle.load(f)
with open('data/prediccionOnline/deliveryModel.pkl', 'rb') as f:
    modelo_tiempo_entrega = pickle.load(f)
with open('data/prediccionOnline/le.pkl', 'rb') as f:
    labelEncoder = pickle.load(f)

vectores = {}

# Conectamos con el servidor de Kafka
client = pykafka.KafkaClient(hosts="localhost:9093")
topic = client.topics['simulation']

###############################################################
# Métodos para obtener el plan de la base de datos y predecir #
###############################################################

# Obtener el plan de la base de datos mongodb
def obtenerPlan(evento):
    return

def actualizarVectores(evento):
    return

def prediccionDeTiempoDeViaje(evento):
    return

def prediccionDeTiempoDeEntrega(evento):
    return

def escribirEnKafka(prediccion):
    return

###########################################################
# Bucle principal: consumir mensajes y hacer predicciones #
###########################################################

# Consumimos los mensajes del topic
consumer = topic.get_simple_consumer( consumer_group='prediccionOnline', 
    reset_offset_on_start=True, 
    auto_offset_reset=OffsetType.LATEST, 
    auto_commit_enable=True, 
    auto_commit_interval_ms=1000)

# Procesamos los mensajes
for evento in consumer:

    # mensaje_evento, en formato json,  como un evento
    evento = json.loads(evento.value.decode('utf-8'))

    # Si no habíamos recibido ningún evento con este simulationId y truck_id, obtenemos su plan desde la base de datos
    if not (evento["simulationId"],evento["truckId"]) in vectores:
        obtenerPlan(evento)

    # Actualizamos el vector correspondiente según el vector de caracterísitcas de cada uno de los modelos
    actualizarVectores(evento)

    # Si el evento es de comienzo de viaje, hacemos una predicción
    if (evento["eventType"] in ["Truck departed", "Truck departed to depot"]):
        prediccion = prediccionDeTiempoDeViaje(evento)
        escribirEnKafka(prediccion)
    # Si el evento es de comienzo de entrega, hacemos una predicción
    elif (evento["eventType"] == "Truck started delivering"):
        prediccion = prediccionDeTiempoDeEntrega(evento)
        escribirEnKafka(prediccion)
    # Si el evento es final de ruta, borramos el vector para liberar memoria
    elif (evento["eventType"] == "Truck ended route"):
        del(vectores[(evento["simulationId"],evento["truckId"])])
