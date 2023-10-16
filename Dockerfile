# Etapa de construcción (instalación de dependencias)
FROM ubuntu:20.04 AS builder

RUN apt update && apt upgrade -y
RUN apt install software-properties-common -y
RUN add-apt-repository ppa:deadsnakes/ppa
RUN apt install -y python3.10
RUN python3.10 --version

RUN apt-get update && apt-get install -y python3-pip

RUN python3 -m pip install -U otree



# Instalar las dependencias del proyecto
# Establecer el directorio de trabajo
WORKDIR .

# Copiar el archivo requirements.txt
COPY . .
#RUN python3 -m pip install -r requirements.txt

# Exponer el puerto 8000 para acceder a oTree
EXPOSE 8000

# Comando para ejecutar oTree
CMD ["otree", "prodserver"]