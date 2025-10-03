#include "esc.h"

 
ESC_Driver::ESC_Driver(int outPin){
    e_stopped = false;
    esc.attach(outPin, 1000, 2000);
}
void ESC_Driver::set_throttle_percent(float throttle){
    if (e_stopped){
        esc.write(0);
        return;
    }
    throttle = throttle > 0.0 ? throttle: 0.0;
    throttle = throttle < 1.0 ? throttle: 1.0;
    esc.write((int)(throttle * 180));
}
float ESC_Driver::get_throttle_percent(){
    return esc.read() / 180.0;
}
void ESC_Driver::begin_calibration(){
    set_throttle_percent(1);
}
void ESC_Driver::end_calibration(){
    set_throttle_percent(0);
}
void ESC_Driver::e_stop(){
    e_stopped = true;
    set_throttle_percent(0);
}