// if the first microcontroller (ESP32) is connected then use the two libraries bellow
#ifdef ESP32
#include <WiFi.h>
#include <AsyncTCP.h>

// if the second microcontroller (ESP8299) is connected then use the  two libraries bellow
#elif defined(ESP8266)
#include <ESP8266WiFi.h>
#include <ESPAsyncTCP.h>
#endif

// importing libraries (#include)
#include <ESPAsyncWebServer.h>

#include "HX711.h"
#include <ArduinoJson.h>
#include <credentials.h>

#include <esc.h>
#include "EEPROM.h"

// defining the inputs/ outputs

  // how long the program will wait for the speed controller 
#define ESC_TIMEOUT 1000

  // the time between transmissions
#define UDP_OUTPUT_BUFF_SIZE 2048

    //loading presaved data 
#define DATA_SAVED_ADDR 0
#define PREF_SAVE_ADDR 1

  // amount of thrust given in newtons
#define DEFAULT_LOAD_CELL_SCALE 127.15

// speed controller pin
#define ESC_PIN 4

 // communication by using the clock pin and the data pin 
#define LOAD_CELL_CK_PIN 2
#define LOAD_CELL_DT_PIN 3

  // measures and controls the current pulled by the motor between 80 and -80 amps
#define CURRENT_SENSE_PIN A0
#define VOLTAGE_SENSE_PIN A1

  // the average between the first 100 samples, temp note: two algorithms: first, measures samples every 20 milliseconds, two, collects 50 samples every second
#define MAX_CURRENT_SAMPLES 100

  //the  max length for the wifi credentials for the thrust test
#define MAX_CREDENTIAL_LENGTH 128
#define CREDENTIAL_WAIT_TIME_S 10

AsyncWebServer server(80);
WiFiUDP udp;

String ssid = "";
String password = "";
String server_ip = "";

const char* PARAM_MESSAGE = "message";
int delay_ms = 20;
void notFound(AsyncWebServerRequest *request) {
    request->send(404, "text/plain", "Not found");
}

long startTime = 0;
int proceedTime = 0;
int lastThrottleRequest = 0;


ESC_Driver esc_driver(ESC_PIN);

bool eeprom_init = false;

// load cell sensor
HX711 load_cell;


JsonDocument data_doc;
JsonObject current_data = data_doc.to<JsonObject>();

struct Prefs {
    float load_cell_offset;
    float load_cell_scale;

    float current_sense_dynamic_err_coef;
    float current_sense_static_err_coef;

    char ssid[MAX_CREDENTIAL_LENGTH]= "";
    char pass[MAX_CREDENTIAL_LENGTH]= "";
    char server_ip[16] = "";
} prefs;

struct {
    float current_sense_readings[MAX_CURRENT_SAMPLES] = { 0.0f };
    int window_size = max(0, min(MAX_CURRENT_SAMPLES, (int)(1000 / delay_ms)));

    int index = 0;

    void update(float val){
        current_sense_readings[index] = val - (val*prefs.current_sense_dynamic_err_coef + prefs.current_sense_static_err_coef);
        index++;
        if(index >= window_size){
            index -= window_size;
        }
    }
    void update_window_size(){
        window_size = max(0, min(MAX_CURRENT_SAMPLES, (int)(1000 / delay_ms)));
    }
    float get_mean(){
        float out = 0.0f;
        for(int i = 0; i < window_size; i++){
            out += (float)current_sense_readings[i] / (float)window_size;
        }
        return out;
    }
} current_sense_data;

void save_prefs() {
    if(eeprom_init){
        EEPROM.write(DATA_SAVED_ADDR, byte(1));
        EEPROM.put(PREF_SAVE_ADDR, prefs);
        EEPROM.commit();
    }
}
void wipe_prefs(){
    if(eeprom_init){
        EEPROM.write(DATA_SAVED_ADDR, byte(0));
        EEPROM.commit();
    }
}
void get_prefs(){
    if(eeprom_init){
        EEPROM.get(PREF_SAVE_ADDR, prefs);
    }
}
bool prefs_saved(){
    if(eeprom_init){
        byte b = byte(EEPROM.read(DATA_SAVED_ADDR));
        return b == (byte) 1;
    }
    return NULL;
}
int get_time(){
    return millis() + startTime;
}

float map_float(float x, float in_min, float in_max, float out_min, float out_max){
    const float run = in_max - in_min;
    if(run == 0){
        Serial.println("map(): Invalid input range, min == max");
        return -1; // AVR returns -1, SAM returns 0
    }
    const float rise = out_max - out_min;
    const float delta = x - in_min;
    return (float)(delta * rise) / (float)run + (float)out_min;
}

float get_current_reading(){
    // map between -188 to 188 instead of -150 to 150 b/c 
    // output voltage on sensor is only 0.5v-.45v.
    // You have to account for the additional range that
    // 0 to 5V provides.
    return -map_float(
        (float) analogRead(CURRENT_SENSE_PIN),
        0.0,
        4095.0,
        -188.0,
        188.0
    );
}

void get_ssid_pass();
void get_server_ip();

void setup_server(){
    server.on("/", HTTP_GET, [](AsyncWebServerRequest *request){
        Serial.print("Recieved Ping at ");
        Serial.print(get_time());
        Serial.println(" ms.");
        request->send(200, "text/plain", "Hello, world");
    });

    server.on("/set_blink_delay", HTTP_POST, [](AsyncWebServerRequest *request){
      String str_msg;
      if (request->hasParam("t")){
        str_msg = request->getParam("t")->value();
        Serial.println(str_msg);
        delay_ms = str_msg.toInt();
      }
      request->send(200, "text/plain", "Set delay: " + str_msg);
    });
    server.on("/calibrate_load_cell", HTTP_POST, [](AsyncWebServerRequest *request){
      String msg;
      if (request->hasParam("weight")){
        msg = request->getParam("weight")->value();
        Serial.println("Recieved Weight" + msg);
        load_cell.calibrate_scale(msg.toInt());
      }
      request->send(200, "text/plain", "Calibration Finished");
    });
    server.on("/tare_load_cell", HTTP_GET, [](AsyncWebServerRequest *request){
      load_cell.tare();
      request->send(200, "text/plain", "Tare Finished");
    });
    server.on("/save_prefs", HTTP_GET, [](AsyncWebServerRequest *request){
        prefs.load_cell_offset = load_cell.get_offset();
        prefs.load_cell_scale = load_cell.get_scale();

        password.toCharArray(prefs.pass, MAX_CREDENTIAL_LENGTH);
        ssid.toCharArray(prefs.ssid, MAX_CREDENTIAL_LENGTH);
        server_ip.toCharArray(prefs.server_ip, 16);

        save_prefs();
        request->send(200, "text/plain", "saved");
    });
    // REPLACED BY UDP STREAM
    // server.on("/get_data", HTTP_GET, [](AsyncWebServerRequest *request){
    //   int bytes_converted = 0;
    //   int length = measureJson(data_store);
    //   char output[length];
    //   serializeJson(data_store, output, length);
    //   request->send(200, "application/json", output);

    //   data_history.clear();

    // });
    server.on("/sync_time", HTTP_POST, [](AsyncWebServerRequest *request){
      String t;
      if (request->hasParam("t")){
        t = request->getParam("t")->value();
        startTime = t.toInt() - millis();
        proceedTime = get_time();
        request->send(200, "text/plain", "Set controller time to " + t);
      }else {
        request->send(400, "text/plain", "Could not set time");
      }
    });
    server.on("/esc_calibration", HTTP_POST, [](AsyncWebServerRequest *request){
        String status;
        if (request->hasParam("status")){
            status = request->getParam("status")->value();
            if (status == "1"){
                esc_driver.begin_calibration();
                Serial.println("Begin esc calibration");
                request->send(200, "text/plain", "calibration started");
            }else {
                esc_driver.end_calibration();
                Serial.println("End esc calibration");
                request->send(200, "text/plain", "calibration ended");
            }

        }
        request->send(400, "text/plain", "Invalid request");
    });
    server.on("/esc_set_throttle", HTTP_POST, [](AsyncWebServerRequest *request){
        String p;
        if (request->hasParam("p")){
            p = request->getParam("p")->value();
            esc_driver.set_throttle_percent(p.toFloat());
            lastThrottleRequest = get_time();
            request->send(200, "text/plain", "throttle set to " + String(esc_driver.get_throttle_percent()));
        }
    });
    server.on("/esc_estop", HTTP_GET, [](AsyncWebServerRequest *request){
        esc_driver.e_stop();
        request->send(200, "text/plain", "estop: true. restart device.");
    });
    server.on("/calibrate_current_sense", HTTP_POST, [](AsyncWebServerRequest * request){
        if(request->hasParam("dec") && request->hasParam("sec")){
            String dec = request->getParam("dec")->value();
            String sec = request->getParam("sec")->value();
            prefs.current_sense_dynamic_err_coef = dec.toFloat();
            prefs.current_sense_static_err_coef = sec.toFloat();
            request->send(200, "text/plain", "Set dec and sec: " + dec + ", " + sec);
        }else{
            request->send(400, "text/plain", "Invalid request! Not enough parameters!");
        }
    });
    server.on("/wipe_prefs", HTTP_GET, [](AsyncWebServerRequest *request){
        wipe_prefs();
        request->send(200, "text/plain", "Wiped");
    });
    server.on("/reset_udp", HTTP_GET, [](AsyncWebServerRequest *request){
        udp.stop();
        request->send(200, "text/plain", "ok");
    });

    server.onNotFound(notFound);

    server.begin();
}

void setup() {
    Serial.begin(115200);
    delay(1000);

    eeprom_init = EEPROM.begin(512);
    if(!eeprom_init){
        Serial.println("Could not initialize EEPROM!");
    } else if(prefs_saved()){
        get_prefs();
    }else{
        load_cell.set_scale(DEFAULT_LOAD_CELL_SCALE);
        prefs.current_sense_dynamic_err_coef = 0.0128f;
        prefs.current_sense_static_err_coef = 4.0f;
    }

    pinMode(LED_BUILTIN, OUTPUT);
    //pinMode(ESC_PIN, OUTPUT);
    pinMode(CURRENT_SENSE_PIN, INPUT);
    pinMode(VOLTAGE_SENSE_PIN, INPUT);

    WiFi.mode(WIFI_STA);
    // Gets the password and SSID from user(else defaults to credentials.h)
    get_ssid_pass();
    // ssid = SSID;
    // password = PASSWORD;
    WiFi.begin(ssid, password);
    if (WiFi.waitForConnectResult() != WL_CONNECTED) {
        Serial.printf("WiFi Failed!\n");
        return;
    }
    Serial.print("IP Address: ");
    Serial.println(WiFi.localIP());
    delay(3000);
    get_server_ip();
    // server_ip = SERVER_IP;

    setup_server();
    load_cell = HX711();
    load_cell.begin(LOAD_CELL_DT_PIN, LOAD_CELL_CK_PIN);
    if(eeprom_init && prefs_saved()){
        load_cell.set_scale(prefs.load_cell_scale);
        load_cell.set_offset(prefs.load_cell_offset);
    }

}

void loop() {
  // Stop motors if they're not actively being commanded to stay on
  if(get_time() > lastThrottleRequest + ESC_TIMEOUT){
    esc_driver.set_throttle_percent(0);
    // Serial.println("Reset throttle due to timeout.");
  }
  // Serial.println(esc_driver.get_throttle_percent());
  // All code below here WILL BE BLOCKED for delay_ms milliseconds
  // DO NOT PUT CRITICAL FUNCATIONALITY HERE
  if(proceedTime > get_time()){
    return;
  }
  proceedTime += delay_ms;


  current_data["timestamp"] =  get_time();
  if(load_cell.is_ready()){
    float measurement = load_cell.get_units();
    current_data["load_cell"] = measurement;
  }
  current_data["esc_percent"] = esc_driver.get_throttle_percent();
  current_sense_data.update_window_size();
  current_sense_data.update(get_current_reading());
  current_data["current_sense"] = current_sense_data.get_mean();

  current_data["voltage_sense"] = map_float(
    analogRead(VOLTAGE_SENSE_PIN),
    0.0, 4095.0,
    0.0, 1.0
  );

  digitalWrite(LED_BUILTIN, !digitalRead(LED_BUILTIN));

  char server_ip_buff[16] = "";
  server_ip.toCharArray(server_ip_buff, 16);
  udp.beginPacket(server_ip_buff, 65432);
  uint8_t output[UDP_OUTPUT_BUFF_SIZE] = { ' ' };  // A single data log should not be more than 2048 characters long
  int written = serializeJson(data_doc, output, UDP_OUTPUT_BUFF_SIZE);
  udp.write(output, written);
  udp.endPacket();

}

void get_ssid_pass(){
    // Prompt for wifi details
    Serial.println("Enter Wifi SSID and password seperated by space...");
    // Wait for input
    int curr_time = millis();
    while(millis() < curr_time + CREDENTIAL_WAIT_TIME_S * 1000 && !Serial.available()){
        delay(10);
    }
    if(Serial.available()){
        // clear ssid and password
        ssid = "";
        password = "";
    } else{
        if(eeprom_init){
            ssid = String(prefs.ssid);
            password = String(prefs.pass);
        }
        Serial.println("Using default credentials");
    }
    bool readSSID = true;
    while (Serial.available())
    {  
        char curr_char = Serial.read();
        if(curr_char == ' '){
            readSSID = false;
            continue;
        }
        if(readSSID){
            ssid.concat(curr_char);
        } else{
            password.concat(curr_char);
        }
    }

    Serial.println("Connecting to: " + ssid);
}

void get_server_ip(){
    // Prompt for wifi details
    Serial.println("Enter Server IP...");
    // Wait for input
    int curr_time = millis();
    while(millis() < curr_time + CREDENTIAL_WAIT_TIME_S * 1000 && !Serial.available()){
        delay(10);
    }
    if(Serial.available()){
        // clear server_ip
        server_ip = "";
    } else{
        if(eeprom_init){
            server_ip = String(prefs.server_ip);
        }
        Serial.println("Using default ip " + server_ip);
    }
    while(Serial.available()){
        server_ip.concat((char)Serial.read());
    }
    Serial.println("Set IP to " + server_ip);
}
