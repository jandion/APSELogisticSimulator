Este documento es una pequeña guía para solucionar los problemas que han aparecido en la clase del martes 11 de marzo.

# Problema 1: Problemas con la biblioteca bson

Este problema se debe a que `pymongo` utiliza una versión especifica de `bson`, si intentamos instalarla manualmente se produce un conflicto. Para solucionarlo, instalaremos solo `pymongo`, eliminando antes `bson` si es que ya lo tenemos instalado.

```bash
pip uninstall bson --yes
pip install pymongo
```

# Problema 2: Problemas con la biblioteca de kafka

Hay dos bibliotecas de Python para Kafka que utilizan el mismo nombre: `pykafka` y `kafka-python`. La que nos interesa en este caso es `kafka-python`. Para instalarla, ejecutamos:

```bash
pip uninstall pykafka --yes
pip install kafka-python
```

# Problema 3: Puertos ya ocupados

Si alguno de los servicios que necesitamos desplegar desde docker-compose ya está siendo usado, podemos modificarlo en el archivo `docker-compose.yml`. Debemos cambiar el puerto en la sección `ports` de la siguiente manera:

Antes:
```yaml
ports:
  - "8080:8080"
```
Después:
```yaml
ports:
  - "8081:8080"
```

**NOTA**: si el puerto aparece mencionado en alguna de las variables de entorno del archivo, también debemos cambiarlo. Por ejemplo, si cambiamos el puerto de mongo, también tendremos que cambiar la variable de mongo-express.
```yaml
environment:
      ME_CONFIG_MONGODB_URL: mongodb://mongo:27017/
```

# Problema 4: Con nada de lo anterior puedo ejecutar el notebook collections.ipynb

Podéis añadir lo siguiente al docker-compose para que os cree un contenedor con jupyter notebook y las librerías necesarias para ejecutar todos los notebooks de la asignatura ya preinstaladas.

```yaml
  jupyter:
    image: ghcr.io/jandion/logisticdeliversimulator/jupyter-apse:latest 
    container_name: jupyter
    ports:
      - "8888:8888"
    environment:
      JUPYTER_ENABLE_LAB: "yes"
```