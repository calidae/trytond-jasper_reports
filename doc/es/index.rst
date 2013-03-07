===============
Informes Jasper
===============

Añade funcionalidad para soportar el uso de informes basados en Jasper.

.. note:: El módulo crea un proceso Java que escucha llamadas XML-RPC en
          localhost para evitar la sobrecarga de la máquina virtual de java
          cada vez que se envía un informe.

          Teniendo en cuenta que se envía el nombre del archivo al proceso
          Java, esto podría ser un problema de seguridad si no se puede confiar
          en los usuarios que pueden establecer conexiones TCP/IP con
          localhost.
