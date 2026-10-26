# Watchman: An Edge-To-Cloud IoT Framework for Honey Bee Monitoring and Predator Detection using Advanced Computer Vision

## Abstract
This document provides a comprehensive technical overview and academic reference for the **Watchman** project, an intelligent, distributed Internet of Things (IoT) framework designed specifically for the protection of API (apiary) environments. The system proposes a low-cost, high-efficiency paradigm by offloading heavy deep neural network computations to a central server while utilizing edge nodes for data acquisition and preliminary motion heuristic filtering. By integrating OpenCV for deterministic algorithmic motion detection and the state-of-the-art YOLOv8x CNN for probabilistic object classification, the system achieves robust real-time threat identification. This documentation covers the underlying algorithms, hardware limitations, memory allocation strategies, network protocols, and cloud integration mechanics.

---

## 1. Introduction
The agricultural sector, particularly apiculture, faces substantial threats from natural predators (e.g., bears, diverse avian species) resulting in significant economic and ecological losses. The **Watchman** framework is introduced as an automated surveillance countermeasure. 

Traditional video streaming surveillance requires massive bandwidth and constant monitoring. Watchman adopts an event-driven architecture, transmitting encapsulated visual data at discrete intervals. To mitigate the computational infeasibility of running advanced deep learning models on resource-constrained microcontrollers like the ESP32, the system employs a bipartite architecture: an Edge Node responsible for image acquisition, and a Central Processing Node utilizing heterogeneous computing (CPU/GPU) to execute complex Convolutional Neural Networks (CNNs).

---

## 2. System Architecture
The Watchman network topology is structurally divided into three distinct operational domains:

1. **The Edge Domain:** Comprising one or multiple ESP32-CAM modules acting as sensory appendages.
2. **The Processing Domain:** A localized HTTP web server instances handling data ingestion, algorithmic preprocessing, and heuristic/AI classification.
3. **The Cloud Interface Domain:** A centralized dashboard hosted by the Blynk IoT platform for asynchronous event logging, telemetry visualization, and Push Notification Service (PNS).

### 2.1 The Edge Node
Equipped with an OV2640 optical sensor, the Edge Node leverages the local Wi-Fi infrastructure to relay discrete topological snapshots encoded in Joint Photographic Experts Group (JPEG) format via multipart HTTP POST multiplexing.

### 2.2 The Central Processing Unit
Constructed upon the Python Flask Web Server Gateway Interface (WSGI), this node acts as the computational powerhouse. It retains temporal state (buffering the preceding frame) to compute optical variance. 

### 2.3 Cloud Integration
An external RESTful API bridges the local computational server to the mobile end-user, establishing an asynchronous, real-time alert protocol without the necessity of static public IP addresses or port forwarding.

---

## 3. Hardware Specifications

### 3.1 Edge Device (ESP32-CAM AI-Thinker)
*   **Microprocessor:** Tensilica Xtensa Dual-Core 32-bit LX6 microprocessor, operating at 160 or 240 MHz.
*   **Memory Architecture:** 520 KB internal SRAM. External Pseudo-Static RAM (PSRAM) is often available (up to 4MB) but fundamentally bypassed in the Watchman firmware in favor of internal DRAM allocation to maximize frame buffer throughput and minimize memory segmentation faults during heavy Wi-Fi transmission.
*   **Optical Sensor (OV2640):** 1/4" CMOS UXGA (1632x1232) image sensor. Hardware is explicitly configured for sub-sampled Video Graphics Array (VGA - 640x480) output parameters with aggressive baseline JPEG compression (`quality factor = 12`) to optimize payload transmission latency.

### 3.2 Processing Node
*   **Recommendation:** A robust computational environment capable of sustained matrix multiplications. An NVIDIA CUDA-enabled Graphical Processing Unit (GPU) is strongly recommended for the Ultralytics YOLOv8x parameter weights.

---

## 4. Methodology and Algorithmic Workflow

The analytical pipeline is executed in a strict chronological sequence to minimize CPU overhead. The computationally expensive Neural Network is conditionally invoked *only* if the deterministic motion algorithm yields a positive boolean flag.

### 4.1 Pixel-Level Motion Detection Heuristics
When frame $F_t$ (current frame at time $t$) is received by the server, it is compared against the globally scoped $F_{t-1}$ (previous frame).

**Step 1: Grayscale Transformation & Smoothing**
To reduce computational dimensionality from 3-channels (RGB) to 1-channel, a luminance extraction is applied:
$Y = 0.299 \cdot R + 0.587 \cdot G + 0.114 \cdot B$

High-frequency sensor noise and lighting micro-fluctuations are mitigated utilizing a significant isotropic Gaussian Blur filter with a kernel size of $K = 21 \times 21$.

**Step 2: Absolute Difference & Binarization**
A temporal difference matrix $D$ is calculated pixel-by-pixel:
$D(X, Y) = | F_{t}(X,Y) - F_{t-1}(X,Y) |$

A global static threshold $\tau = 35$ is applied to convert the continuous difference image into a binary mask $B$:
$$ B(X, Y) = \begin{cases} 255, & \text{if } D(X, Y) > \tau \\ 0, & \text{otherwise} \end{cases} $$

**Step 3: Morphological Dilation & Spatial Contour Analysis**
The resulting binary mask undergoes morphological dilation (2 iterations) to bridge disconnected anomalous pixels belonging to the same kinetic object. Suzuki's topological structural analysis algorithm (`cv2.findContours`) retrieves external boundaries. Any contour with an area localized bounding box $A_c < 1000$ pixels is discarded as erratic noise.

### 4.2 Deep Learning Object Recognition (YOLOv8x)
If the heuristic function derives $\text{Motion} = \text{True}$, the original $F_t$ matrix is passed into the Ultralytics YOLOv8-Extra Large model. 
1.  **Inference:** Computes spatial bounding boxes $b = (x, y, w, h)$, Objectness probability $P(Obj)$, and discrete class probabilities $P(C_i|Obj)$.
2.  **Filtering Parameter Set:** The architecture deliberately ignores non-threatening classifications (e.g., humans, vehicles). The intersection subset focuses strictly on COCO identifiers: `[14, 15, 16, 17, 18, 19, 20, 21, 22, 23]`, encompassing birds, domestic and feral animals, up to macroscopic threats like bears and elephants.
3.  **Confidence Thresholding:** A moderately aggressive threshold coefficient of $\beta = 0.40$ is mandated to maximize the Recall-Precision equilibrium, ensuring minimal false negatives for apiculture protection. 

---

## 5. Detailed Implementation Paradigm

### 5.1 Edge Firmware Optimization (`esp32_cam.ino`)
The firmware implements critical low-level register manipulations:
*   **Brownout Disablement:** Overriding hardware safeguards `WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0)`. Transmission power spikes when the Wi-Fi transceiver engages occasionally dip the 3.3v logic line. Disabling the watchdog avoids catastrophic boot looping.
*   **DRAM over PSRAM Allocation:** Due to timing inaccuracies and I/O bottlenecks accessing external PSRAM during frame buffer initialization (`esp_camera_fb_get`), the system rigidly reallocates the buffer memory space to Internal RAM utilizing `config.fb_location = CAMERA_FB_IN_DRAM`.
*   **Garbage Collection Protocol:** Upon transmission finalization within the socket loop, the frame buffer pointer is immediately reallocated back to the heap via `esp_camera_fb_return(fb)` to prevent progressive memory leaks inside the `while(true)` lifecycle.
*   **Persistent Socket Configuration:** Post camera-initialization, `WiFi.setSleep(false)` is enacted. Disabling Wi-Fi MAC layer sleep protocols guarantees high-availability during the 30-second cyclical wake intervals without relying on heavy deep-sleep/re-association delays.

### 5.2 Server Web Application Design (`server.py`)
Flask handles concurrent threading intuitively over WSGI. 
*   **Multipart Parser:** Expects an `imageFile` payload, subsequently saving the object buffer sequentially into the `/uploads` directory utilizing ISO 8601 derived timestamp nomenclature.
*   **Static File Serving Routing:** The `/detections/<filename>` endpoint enables the remote cloud dashboard (Blynk UI) to fetch dynamically annotated image arrays over the WAN.
*   **Asynchronous Analytics:** The OpenCV blocking methods run sequentially before dispatching an HTTP Success code (200), meaning frame latency is inherently matched to inference latency.

### 5.3 RESTful Communication & Telemetry Layer
Integration with Blynk Cloud is executed symmetrically via HTTPS endpoints using URL string formatting:
*   **Data Stream V1 (Status Identifier):** Signals real-time kinetic presence.
*   **Data Stream V2 (Gallery Array Pointer):** Transposes the URL property metadata string `urls={image_url}` and triggers widget refresh by setting Value = 1.
*   **Event Logging:** Executable `predator_alert` issues push notifications out of band.

---

## 6. Software Stack & Critical Dependencies

| Domain | Dependency | Version / Reference | Function |
| :--- | :--- | :--- | :--- |
| **Edge OS** | Arduino Core for ESP32 | v2.0+ | HAL and RTOS task scheduling |
| **Edge Vision** | `esp32_camera.h` | 2.0.x | Direct optical sensor DMA interfacing |
| **Host Backend** | Python | 3.9+ | Main runtime environment |
| **API Framework**| Flask | latest | WSGI routing for incoming visual telemetry |
| **Vision DSP** | OpenCV (`opencv-python-headless`)| 4.x | Frame extraction, masking, morphological shifts |
| **Deep Learning**| Ultralytics YOLO | 8.x.x | Cross-stage Partial Network for bounding box inferences |
| **Networking** | Requests | latest | REST bridging to remote cloud platform |

---

## 7. Experimental Setup and Execution Guidelines

### 7.1 Peripheral Installation
1. Obtain the codebase matrix via git clone/download.
2. Initialize virtual environments as per Python PEP conventions.
3. Install package distributions: `pip install -r requirements.txt`. Note: Local builds of PyTorch matching your specific CUDA compilation are recommended before running the constraint files to ensure GPU offloading.

### 7.2 Variable Configurations
Alter the global static descriptors inside `server.py`:
*   `BLYNK_AUTH_TOKEN`: Replaced with cryptographic 32-character key from the Blynk interface.
*   `SERVER_IP`: Must hold the un-natted local broadcast address facing the EPS32 subnet structure.
Configure the equivalent string variables inside `esp32_cam.ino`. 

### 7.3 Boot Sequence Protocol
1. Instantiate the Python application node: `python server.py`. 
2. Ensure the firewall protocols (e.g., Windows Defender) are perforated at TCP Port 5000 to allow inbound non-standard HTTP traversal.
3. Apply a stable 5V current source to the ESP32 array; monitor the Serial COM port at an elevated baud rate of `115200` to verify structural integrity and successful `POST /upload` handshakes.

---

## 8. Conclusion
The **Watchman** architecture provides a highly scalable paradigm for edge-to-cloud security applications. By strategically avoiding executing mathematically bound deep neural networks on constrained end-point silicon and instead relying on high-reliability, low-latency transmission for central processing, the framework maximizes detection accuracy while keeping deployment footprint economical and robust. The heuristic motion gating prevents total computational saturation of the central server, rendering the system ecologically and procedurally viable for persistent honey bee surveillance operations.
