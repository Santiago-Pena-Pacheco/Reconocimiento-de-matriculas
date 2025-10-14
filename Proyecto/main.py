import cv2
import numpy as np
import pytesseract
from PIL import Image
from datetime import datetime
import re

# Usuarios registrados
usuarios = {
    "ABC 123": {"nombre": "Carlos PLazas", "cedula": "123456789", "tipo": "profesor"},
    "DEF 234": {"nombre": "German Mendez", "cedula": "234567891", "tipo": "profesor"},
    "MNO 321": {"nombre": "Pedro Forero", "cedula": "321456789", "tipo": "profesor"},
    "VWX 159": {"nombre": "Carlos Piña", "cedula": "159753486", "tipo": "profesor"},
    "EFG 951": {"nombre": "Daniel Castro", "cedula": "951357486", "tipo": "profesor"},
    "NOP 258": {"nombre": "Mauricio Moncada", "cedula": "258147369", "tipo": "profesor"},
    "WXY 654": {"nombre": "Oscar Medina", "cedula": "654321987", "tipo": "profesor"},
    "FGH 258": {"nombre": "Sandra Leon", "cedula": "258963741", "tipo": "profesor"},
    "PQS 654": {"nombre": "Hector Beltran", "cedula": "654987321", "tipo": "profesor"},
    "XYZ 258": {"nombre": "Carolina Nieto", "cedula": "258741963", "tipo": "profesor"},
    "XYZ 789": {"nombre": "Ana Gomez", "cedula": "987654321", "tipo": "estudiante"},
    "GHI 567": {"nombre": "Mateo Roberto", "cedula": "567891234", "tipo": "estudiante"},
    "PQR 654": {"nombre": "Laura Torres", "cedula": "654789123", "tipo": "estudiante"},
    "YZA 753": {"nombre": "Pablo Montoya", "cedula": "753951486", "tipo": "estudiante"},
    "HIJ 147": {"nombre": "Pablo Carreño", "cedula": "147258369", "tipo": "estudiante"},
    "QRS 741": {"nombre": "steven stiqui", "cedula": "741852963", "tipo": "estudiante"},
    "ZAB 147": {"nombre": "Natalia Vargas", "cedula": "147369258", "tipo": "estudiante"},
    "IJK 741": {"nombre": "Esteban Cruz", "cedula": "741963852", "tipo": "estudiante"},
    "RTU 147": {"nombre": "Monica Reyes", "cedula": "147852369", "tipo": "estudiante"},
    "ABC 741": {"nombre": "Mauricio Silva", "cedula": "741369852", "tipo": "estudiante"},
    "LMN 456": {"nombre": "Luis Torres", "cedula": "456789123", "tipo": "estudiante"},
    "JKL 890": {"nombre": "Sofia Ramirez", "cedula": "890123456", "tipo": "estudiante"},
    "STU 987": {"nombre": "Andres Gomez", "cedula": "987123456", "tipo": "estudiante"},
    "BCD 852": {"nombre": "Camila Ruiz", "cedula": "852963741", "tipo": "estudiante"},
    "KLM 369": {"nombre": "Jorge Molina", "cedula": "369258147", "tipo": "estudiante"},
    "TUV 963": {"nombre": "Patricia Mejia", "cedula": "963741852", "tipo": "estudiante"},
    "CDE 369": {"nombre": "Raul Pineda", "cedula": "369147258", "tipo": "estudiante"},
    "LMO 963": {"nombre": "Daniela Salas", "cedula": "963258741", "tipo": "estudiante"},
    "UVW 369": {"nombre": "Julian Navarro", "cedula": "369741258", "tipo": "estudiante"},
    "DEF 963": {"nombre": "Angela Mora", "cedula": "963147258", "tipo": "estudiante"},
    "MOT 12A": {"nombre": "Nicolas Copernico", "cedula": "777888999", "tipo": "estudiante"},
    "CYC 50B": {"nombre": "Elena Nito", "cedula": "111222333", "tipo": "profesor"},
    "RUT 99Z": {"nombre": "Javier Rueda", "cedula": "444555666", "tipo": "estudiante"},
}

plazas = {
    "profesor": {"disponibles": 10, "tarifa": 2500},
    "estudiante": {"disponibles": 20, "tarifa": 5000},
    "visitante": {"disponibles": 10, "tarifa": 15000}
}

registro_vehiculos = {}

# Variables de control
placa_detectada = ""
placa_en_proceso = None
factura_generada = False
hora_ingreso = None
modo_operacion = None
estado_evento = None
estado_salida = None
estado_lleno = None
estado_advertencia = None
tiempo_inicio_evento = None
deteccion_activa = True
ventanas_temporales = {}
Ctexto = ""
factura_frame = None
plazas_frame = None
plazas_frame_salida = None

def mostrar_ventana_temporal(nombre, imagen, duracion=5):
    ventanas_temporales[nombre] = {
        "imagen": imagen,
        "inicio": datetime.now(),
        "duracion": duracion,
        "mostrada": False
    }

def actualizar_ventanas_temporales():
    ahora = datetime.now()
    ventanas_a_cerrar = []
    for nombre, datos in ventanas_temporales.items():
        if (ahora - datos["inicio"]).total_seconds() < datos["duracion"]:
            cv2.imshow(nombre, datos["imagen"])
            datos["mostrada"] = True
        else:
            if datos["mostrada"]:
                ventanas_a_cerrar.append(nombre)
    for nombre in ventanas_a_cerrar:
        cv2.destroyWindow(nombre)
        del ventanas_temporales[nombre]

# ruta a la aplicacion tesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Con 0 para camara por defecto y 1 para camara complementaria
cap = cv2.VideoCapture(1)

# Proceso de reconoconocimiento hasta oprimir ESC
while True:
    ret, frame = cap.read()
    if not ret:
        break

    ahora = datetime.now()

    # Control de eventos temporales (Secuencia de ventanas en el INGRESO)
    if not deteccion_activa:
        if estado_evento and (ahora - tiempo_inicio_evento).total_seconds() >= 5:
            if estado_evento == "bienvenida" and factura_frame is not None:
                estado_evento = "factura"
                tiempo_inicio_evento = ahora
                mostrar_ventana_temporal("Factura de Ingreso", factura_frame, duracion=5)

            elif estado_evento == "factura" and plazas_frame is not None:
                estado_evento = "plazas"
                tiempo_inicio_evento = ahora
                mostrar_ventana_temporal("Plazas Disponibles", plazas_frame, duracion=5)

            elif estado_evento == "plazas":
                estado_evento = None
                deteccion_activa = True
                factura_generada = True
                placa_detectada = ""

        # Control de eventos temporales (Secuencia de ventanas en la SALIDA)
        elif estado_salida == "salida" and (ahora - tiempo_inicio_evento).total_seconds() >= 5 and plazas_frame_salida is not None:
            mostrar_ventana_temporal("Plazas tras salida", plazas_frame_salida, duracion=5)
            estado_salida = "plazas_salida"
            tiempo_inicio_evento = ahora

        elif estado_salida == "plazas_salida" and (ahora - tiempo_inicio_evento).total_seconds() >= 5:
            estado_salida = None
            deteccion_activa = True

        # Control de eventos temporales (Lleno o Advertencia)
        elif estado_lleno == "lleno" and (ahora - tiempo_inicio_evento).total_seconds() >= 5:
            estado_lleno = None
            deteccion_activa = True

        elif estado_advertencia == "espera" and (ahora - tiempo_inicio_evento).total_seconds() >= 5:
            estado_advertencia = None
            deteccion_activa = True

    if deteccion_activa:
        alto, ancho, _ = frame.shape
        x1, x2 = int(ancho / 3), int(ancho * 2 / 3)
        y1, y2 = int(alto / 3), int(alto * 2 / 3)

        # Recuadro verde para el área de interés
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        recorte = frame[y1:y2, x1:x2]

        # Detecccion de placa con filtro De escala de grises

        gris = cv2.cvtColor(recorte, cv2.COLOR_BGR2GRAY)
        suavizado = cv2.GaussianBlur(gris, (5, 5), 0)

        bordes_canny = cv2.Canny(suavizado, 100, 200)
        bordes_canny = cv2.dilate(bordes_canny, None, iterations=1)

        # ventana con Reconocimiento en tiempo real
        cv2.imshow("Bordes De La Placa en tiempo real", bordes_canny)

        contornos, _ = cv2.findContours(bordes_canny, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

        mejor_placa = None
        mejor_area = 0 # Con 0 para buscar el contorno más grande que cumpla

        # Filtrado y procesamiento de contornos
        for contorno in contornos:
            area = cv2.contourArea(contorno)

            # Ajuste en rango de área y búsqueda del contorno con mayor área dentro de los parámetros
            if 1000 < area < 30000 and area > mejor_area:

                x, y, w, h = cv2.boundingRect(contorno)
                aspect_ratio = w / h

                if 2.0 < aspect_ratio < 5.5:

                    perimetro = cv2.arcLength(contorno, True)
                    approx = cv2.approxPolyDP(contorno, 0.04 * perimetro, True)

                    # El contorno debe ser rectangular (4 vértices)
                    if len(approx) == 4:
                        mejor_placa = (x, y, w, h)
                        mejor_area = area # Se actualiza para buscar un contorno aún mejor

        # Procesar el mejor contorno encontrado
        if mejor_placa is not None:
            x, y, w, h = mejor_placa

            # recuadro cian (255, 255, 0) sobre el recorte, usando las coordenadas relativas (x, y, w, h)
            cv2.rectangle(recorte, (x, y), (x + w, y + h), (255, 255, 0), 2)  # Cian

            # Asegurar que el recorte de la placa es válido antes de OCR (Reconocimiento optico de caracteres)
            if y >= 0 and y + h <= recorte.shape[0] and x >= 0 and x + w <= recorte.shape[1]:
                placa_recortada = recorte[y:y + h, x:x + w]

                gris_placa = cv2.cvtColor(placa_recortada, cv2.COLOR_BGR2GRAY)

                binarizada = cv2.adaptiveThreshold(gris_placa, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,cv2.THRESH_BINARY, 11, 2)

                if np.mean(binarizada) < 127:
                    binarizada = 255 - binarizada

                #Registra la deteccion al final del reconocimiento 
                #cv2.imshow("Imagen Binarizada", binarizada) 

                # Preparar y pasar a Tesseract
                bin_img = Image.fromarray(binarizada).convert("L")

                alp, anp = binarizada.shape
                if alp >= 20 and anp >= 50:
                    # psm8 detecta toda la fila de caracteres
                    config_ocr = "--psm 8 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
                    texto = pytesseract.image_to_string(bin_img, config=config_ocr)
                    texto = texto.strip().upper().replace("\n", "").replace(" ", "")

                    # Formatear el texto crudo del OCR para validación
                    placa_cruda = texto.strip().upper().replace(" ", "")
                    
                    placa_detectada = ""
                    placa_formateada = ""

                    # Patrón para carro: (3 letras, 3 números)
                    patron_carro = re.compile(r'^[A-Z]{3}[0-9]{3}$')
                    # Patrón para moto: (3 letras, 2 números, 1 letra)
                    patron_moto = re.compile(r'^[A-Z]{3}[0-9]{2}[A-Z]{1}$')
                    
                    if len(placa_cruda) == 6:
                        if patron_carro.match(placa_cruda):
                            placa_formateada = f"{placa_cruda[:3]} {placa_cruda[3:]}"
                        elif patron_moto.match(placa_cruda):
                            # Formato de moto:
                            placa_formateada = f"{placa_cruda[:3]} {placa_cruda[3:]}"
                    
                    if placa_formateada:
                        placa_detectada = placa_formateada
                        Ctexto = placa_detectada
                        factura_generada = False
                        hora_ingreso = datetime.now()
                        modo_operacion = "salida" if placa_detectada in registro_vehiculos else "ingreso"

                # Advertencia si falla el OCR
                if not placa_detectada and mejor_placa is not None: # Verifica que haya un contorno detectado
                    advertencia = np.zeros((200, 600, 3), dtype=np.uint8)
                    cv2.putText(advertencia, "Mantenga el vehiculo quieto", (100, 80), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                    cv2.putText(advertencia, "para reconocer su placa", (100, 140), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)

                    mostrar_ventana_temporal("Advertencia", advertencia, duracion=5)
                    estado_advertencia = "espera"
                    tiempo_inicio_evento = datetime.now()
                    deteccion_activa = False

    # Mostrar placa detectada
    cv2.rectangle(frame, (870, 750), (1070, 850), (8, 0, 0), cv2.FILLED)
    cv2.putText(frame, Ctexto, (880, 810), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 8), 2)

    # Procesar ingreso 
    if placa_detectada and not factura_generada and modo_operacion == "ingreso":
        tipo = usuarios.get(placa_detectada, {"tipo": "visitante"})["tipo"]
                        if placa_detectada not in usuarios:
            usuarios[placa_detectada] = {"nombre": "Visitante", "cedula": "N/A", "tipo": tipo}

        # Aumenta o disminuye las plazas
        if placa_detectada not in registro_vehiculos:
            if plazas[tipo]["disponibles"] > 0:
                plazas[tipo]["disponibles"] -= 1
                tarifa = plazas[tipo]["tarifa"]
                fecha = hora_ingreso.strftime("%d/%m/%Y")
                hora = hora_ingreso.strftime("%H:%M:%S")

                # Ventana facuracion
                factura_frame = np.zeros((450, 600, 3), dtype=np.uint8)
                cv2.putText(factura_frame, "FACTURA", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 200, 0), 3)
                cv2.putText(factura_frame, f"Bienvenido {usuarios[placa_detectada]['nombre']}", (20, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
                cv2.putText(factura_frame, f"Placa: {placa_detectada}", (20, 140), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
                cv2.putText(factura_frame, f"Tipo: {tipo}", (20, 180), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
                cv2.putText(factura_frame, f"Tarifa: ${tarifa}", (20, 220), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
                cv2.putText(factura_frame, f"Fecha: {fecha}", (20, 260), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
                cv2.putText(factura_frame, f"Hora ingreso: {hora}", (20, 300), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

                # Ventana Plazas disponibles
                plazas_frame = np.zeros((200, 600, 3), dtype=np.uint8)
                cv2.putText(plazas_frame, f"Plazas disponibles para {tipo}: {plazas[tipo]['disponibles']}", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
                
                # Ventana de bienvenida 
                acceso_frame = np.zeros((200, 600, 3), dtype=np.uint8)
                cv2.putText(acceso_frame, "Acceso autorizado", (50, 80), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 3)
                cv2.putText(acceso_frame, "Bienvenido al parqueadero", (50, 140), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

                mostrar_ventana_temporal("Barrera de Ingreso", acceso_frame, duracion=5)

                deteccion_activa = False
                estado_evento = "bienvenida"
                tiempo_inicio_evento = datetime.now()
                registro_vehiculos[placa_detectada] = {"ingreso": hora_ingreso}
                placa_en_proceso = placa_detectada
            else:
                # ventana plazas llenas 
                lleno_frame = np.zeros((200, 600, 3), dtype=np.uint8)
                cv2.putText(lleno_frame, "PLAZAS LLENAS", (150, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 255), 3)
                cv2.putText(lleno_frame, "VUELVA MAS TARDE", (150, 150), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (0, 255, 255), 3)

                mostrar_ventana_temporal("Estado de Parqueadero", lleno_frame, duracion=5)
                estado_lleno = "lleno"
                tiempo_inicio_evento = datetime.now()
                deteccion_activa = False
                factura_generada = True

    # Procesar salida 
    if placa_detectada and not factura_generada and modo_operacion == "salida":
        if placa_detectada in registro_vehiculos:
            hora_salida = datetime.now()
            hora_ingreso = registro_vehiculos[placa_detectada]["ingreso"]
            tiempo = hora_salida - hora_ingreso
            tipo = usuarios.get(placa_detectada, {"tipo": "visitante"})["tipo"]

            plazas[tipo]["disponibles"] += 1
            del registro_vehiculos[placa_detectada]

            # Ventana salida autorizada
            salida_frame = np.zeros((200, 600, 3), dtype=np.uint8)
            cv2.putText(salida_frame, "Salida autorizada", (50, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 3)
            cv2.putText(salida_frame, f"La placa {placa_detectada}", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
            cv2.putText(salida_frame, f"salio a las {hora_salida.strftime('%H:%M:%S')}", (50, 140), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
            cv2.putText(salida_frame, f"Tiempo total: {str(tiempo).split('.')[0]}", (50, 180), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

            mostrar_ventana_temporal("Salida de Vehiculo", salida_frame, duracion=5)

            plazas_frame_salida = np.zeros((200, 600, 3), dtype=np.uint8)
            cv2.putText(plazas_frame_salida, f"Plazas disponibles para {tipo}: {plazas[tipo]['disponibles']}", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)

            estado_salida = "salida"
            tiempo_inicio_evento = datetime.now()
            deteccion_activa = False
            factura_generada = True
            placa_en_proceso = None
            placa_detectada = ""

    # Actualizar ventanas y mostrar cámara
    actualizar_ventanas_temporales()
    cv2.imshow("Camara - Deteccion de Placa", frame)

    if cv2.waitKey(1) == 27:
        break

cap.release()
cv2.destroyAllWindows()
