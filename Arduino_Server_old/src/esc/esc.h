#pragma once
#include <ESP32PWM.h>
#include <ESP32Servo.h>

class ESC_Driver{
private:
Servo esc;
bool e_stopped;

public:
    ESC_Driver(int escPin);
    void set_throttle_percent(float throttle);
    float get_throttle_percent();
    void begin_calibration();
    void end_calibration();
    void e_stop();
};