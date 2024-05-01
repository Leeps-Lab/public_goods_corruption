# Public Goods Corruption

## Instalación

Para instalar y ejecutar este proyecto, asegúrate de tener Docker instalado en tu sistema.

1. Clona este repositorio en tu máquina local:

2. Navega al directorio del repositorio:

    ```
    cd public_goods_corruption
    ```

3. Construye la imagen de Docker utilizando el Dockerfile proporcionado:

    ```
    docker build -t public_goods_corruption .
    ```

4. Una vez que la imagen se haya construido correctamente, puedes ejecutar un contenedor basado en esta imagen:

    ```
    docker run -d -p 80:8000 public_goods_corruption
    ```

    Este comando ejecutará el contenedor en segundo plano y expondrá el puerto 80 de tu máquina local al puerto 8000 del contenedor.

5. Accede a la aplicación en tu navegador web visitando `http://localhost:80`.



## Detener y Eliminar un Contenedor

Si deseas detener o eliminar el contenedor Docker, sigue estos pasos:

1. Listar contenedores activos:

    ```
    docker ps
    ```

1. Detener el contenedor con el id:

    ```
    docker stop id-contenedor
    ```

    Esto detendrá el contenedor en ejecución sin eliminarlo.

2. Eliminar el contenedor:

    ```
    docker rm id-contenedor
    ```

    Esto eliminará el contenedor Docker.