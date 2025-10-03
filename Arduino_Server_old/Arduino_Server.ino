//
// A simple server implementation showing how to:
//  * serve static messages
//  * read GET and POST parameters
//  * handle missing pages / 404s
//

#include <Arduino.h>
#ifdef ESP32
#include <WiFi.h>
#include <AsyncTCP.h>
#elif defined(ESP8266)
#include <ESP8266WiFi.h>
#include <ESPAsyncTCP.h>
#endif
#include <ESPAsyncWebSrv.h>

#include "HX711.h"
#include <ArduinoJson.h>
#include "src/credentials.h"

#include "src/esc/esc.h"
#include "EEPROM.h"

#define ESC_TIMEOUT 1500

#define DATA_SAVED_ADDR 0
#define PREF_SAVE_ADDR 1

#define DEFAULT_LOAD_CELL_SCALE 127.15

#define ESC_PIN 5
#define LOAD_CELL_CK_PIN 2
#define LOAD_CELL_DT_PIN 3
#define CURRENT_SENSE_PIN A0

AsyncWebServer server(80);

const char* ssid = SSID;
const char* password = PASSWORD;

const char* PARAM_MESSAGE = "message";
int delay_ms = 100;
void notFound(AsyncWebServerRequest *request) {
    request->send(404, "text/plain", "Not found");
}

long startTime = 0;
int proceedTime = 0;
int lastThrottleRequest = 0;
int sample_size = 100;

ESC_Driver esc_driver(ESC_PIN);

bool eeprom_init = false;

// load cell sensor
HX711 load_cell;


JsonDocument data_store;
JsonArray data_history;

JsonDocument temp_cd;
JsonObject current_data = temp_cd.to<JsonObject>();

struct Prefs {
    float load_cell_offset;
    float load_cell_scale;
} prefs;

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
    return map_float(
        (float) analogRead(CURRENT_SENSE_PIN),
        0.0,
        4095.0,
        -188.0,
        188.0
    );
}

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
    server.on("/save_load_cell_config", HTTP_GET, [](AsyncWebServerRequest *request){
        prefs.load_cell_offset = load_cell.get_offset();
        prefs.load_cell_scale = load_cell.get_scale();
        save_prefs();
        request->send(200, "text/plain", "saved");
    });
    server.on("/get_data", HTTP_GET, [](AsyncWebServerRequest *request){
      int bytes_converted = 0;
      int length = measureJson(data_store);
      char output[length];
      serializeJson(data_store, output, 256);
      request->send(200, "application/json", output);

      data_history.clear();

    });
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
        }
        request->send(200, "text/plain", "throttle set to" + p);
    });
    server.on("/esc_estop", HTTP_GET, [](AsyncWebServerRequest *request){
        esc_driver.e_stop();
        request->send(200, "text/plain", "estop: true. restart device.");
    });
    server.on("/wipe_prefs", HTTP_GET, [](AsyncWebServerRequest *request){
        wipe_prefs();
        request->send(200, "text/plain", "Wiped");
    });

    server.onNotFound(notFound);

    server.begin();
}

void setup() {

    Serial.begin(115200);
    pinMode(LED_BUILTIN, OUTPUT);
    pinMode(CURRENT_SENSE_PIN, INPUT);

    WiFi.mode(WIFI_STA);
    WiFi.begin(ssid, password);
    if (WiFi.waitForConnectResult() != WL_CONNECTED) {
        Serial.printf("WiFi Failed!\n");
        return;
    }
    Serial.print("IP Address: ");
    Serial.println(WiFi.localIP());

    setup_server();
    load_cell = HX711();
    load_cell.begin(LOAD_CELL_DT_PIN, LOAD_CELL_CK_PIN);

    data_history = data_store["data_history"].to<JsonArray>();

    eeprom_init = EEPROM.begin(64);
    if(eeprom_init){
        Serial.println("Could not initialize EEPROM!");
    }
    delay(50);
    if(prefs_saved()){
        get_prefs();
        load_cell.set_scale(prefs.load_cell_scale);
        load_cell.set_offset(prefs.load_cell_offset);
    }else{
        load_cell.set_scale(DEFAULT_LOAD_CELL_SCALE);
    }

}

void loop() {
  // Stop motors if they're not actively being commanded to stay on
  if(get_time() > lastThrottleRequest + ESC_TIMEOUT){
    esc_driver.set_throttle_percent(0);
  }

  // All code below here WILL BE BLOCKED for delay_ms milliseconds
  // DO NOT PUT CRITICAL FUNCATIONALITY HERE
  if(proceedTime > get_time()){
    return;
  }

  proceedTime += delay_ms;
  if(data_history.size() >= sample_size){
    data_history.remove(0);
  }


  current_data["timestamp"] =  get_time();
  if(load_cell.is_ready()){
    float measurement = load_cell.get_units();
    current_data["load_cell"] = measurement;
  }
  current_data["esc_percent"] = esc_driver.get_throttle_percent();
  current_data["current_sense"] = get_current_reading();

  digitalWrite(LED_BUILTIN, !digitalRead(LED_BUILTIN));
  data_history.add(current_data);
//   delay(delay_ms);
  Serial.println(get_current_reading());
}