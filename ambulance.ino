#include <EveryTimer.h>
#define PERIOD_MS 1000
EveryTimer timer;
bool active = true;
#define BLYNK_PRINT Serial
#include <WiFi.h>
#include <WiFiClient.h>
#include <BlynkSimpleEsp32.h>
#define BLYNK_TEMPLATE_ID "TMPL3JSkzI6eB"
#define BLYNK_TEMPLATE_NAME "Traficlight"
#define BLYNK_AUTH_TOKEN "3D5AgpyH94GcV2HvA4tuoo26r_tOstj2"
#include <LCD_I2C.h>
LCD_I2C lcd(0x27);
unsigned long lastConnectionTime = 0;
long lastUpdateTime = 0;
const char* ssid = "IOT";
const char* password = "123456789";// flag =0
char auth[] = BLYNK_AUTH_TOKEN;
//------signal-1--------//
#define green1 18
#define yellow1 19
#define red1 15
//------signal-2--------//
#define green2 2
#define yellow2 4
#define red2 5
//------signal-3--------//
#define green3 25
#define yellow3 33
#define red3 32
//------signal-4--------//
#define green4 14
#define yellow4 26
#define red4 27
int sec;
void setup()
{
Serial.begin(9600);
pinMode(green1, OUTPUT);
pinMode(yellow1, OUTPUT);
pinMode(red1, OUTPUT);
pinMode(green2, OUTPUT);
pinMode(yellow2, OUTPUT);
pinMode(red2, OUTPUT);
pinMode(green3, OUTPUT);
pinMode(yellow3, OUTPUT);
pinMode(red3, OUTPUT);
timer.Every(PERIOD_MS, action);
pinMode(green4, OUTPUT);
pinMode(yellow4, OUTPUT);
pinMode(red4, OUTPUT);
digitalWrite(green1, HIGH);
digitalWrite(yellow1, HIGH);
digitalWrite(red1, LOW);
digitalWrite(green2, HIGH);
digitalWrite(yellow2, HIGH);
digitalWrite(red2, HIGH);
digitalWrite(green3, HIGH);
digitalWrite(yellow3, HIGH);
digitalWrite(red3, HIGH);
digitalWrite(green4, HIGH);
digitalWrite(yellow4, HIGH);
digitalWrite(red4, HIGH);
lcd.begin();
lcd.backlight();
lcd.setCursor(0, 0);
lcd.print("TRAFFIC SIGNAL");
Blynk.begin(auth, ssid, password, "blynk.cloud", 80);
lcd.clear();
signalone();
}
void loop()
{
automatic();
Blynk.run();
delay(200);
}
void signalone()
{
lcd.setCursor(0, 0);
lcd.print("SIGNAL 1");
Serial.println("SINGAL ONE");
digitalWrite(green1, HIGH); digitalWrite(yellow1, LOW); digitalWrite(red1, LOW);
digitalWrite(green2, LOW); digitalWrite(yellow2, HIGH); digitalWrite(red2, LOW);
digitalWrite(green3, LOW); digitalWrite(yellow3, LOW); digitalWrite(red3, HIGH);
digitalWrite(green4, LOW); digitalWrite(yellow4, LOW); digitalWrite(red4, HIGH);
}
void signaltwo()
{
lcd.setCursor(0, 0);
lcd.print("SIGNAL 2");
Serial.println("SINGAL TWO");
digitalWrite(green1, LOW); digitalWrite(yellow1, LOW); digitalWrite(red1, HIGH);
digitalWrite(green2, HIGH); digitalWrite(yellow2, LOW); digitalWrite(red2, LOW);
digitalWrite(green3, LOW); digitalWrite(yellow3, HIGH); digitalWrite(red3, LOW);
digitalWrite(green4, LOW); digitalWrite(yellow4, LOW); digitalWrite(red4, HIGH);
}
void signalthree()
{
lcd.setCursor(0, 0);
lcd.print("SIGNAL 3");
Serial.println("SINGAL THREE");
digitalWrite(green1, LOW); digitalWrite(yellow1, LOW); digitalWrite(red1, HIGH);
digitalWrite(green2, LOW); digitalWrite(yellow2, LOW); digitalWrite(red2, HIGH);
digitalWrite(green3, HIGH); digitalWrite(yellow3, LOW); digitalWrite(red3, LOW);
digitalWrite(green4, LOW); digitalWrite(yellow4, HIGH); digitalWrite(red4, LOW);
}
void signalfour()
{
lcd.setCursor(0, 0);
lcd.print("SIGNAL 4");
Serial.println("SINGAL FOUR");
digitalWrite(green1, LOW); digitalWrite(yellow1, HIGH); digitalWrite(red1, LOW);
digitalWrite(green2, LOW); digitalWrite(yellow2, LOW); digitalWrite(red2, HIGH);
digitalWrite(green3, LOW); digitalWrite(yellow3, LOW); digitalWrite(red3, HIGH);
digitalWrite(green4, HIGH); digitalWrite(yellow4, LOW); digitalWrite(red4, LOW);
}
void action()
{
sec++;
}
BLYNK_WRITE(V0)
{
int button = param.asInt(); // read button
if (button == 1 )
{
Serial.println("signalone");
signalone();
delay(8000);
}
else if (button == 2)
{
Serial.println("signaltwo");
signaltwo();
delay(8000);
}
else if (button == 3)
{
Serial.println("signalthree");
signalthree();
delay(8000);
}
else if (button == 4)
{
Serial.println("signalfour");
signalfour();
delay(8000);
}
}
void automatic()
{
timer.Update();
if (sec == 30) {
Serial.println("SIGNAL FOUR AUTOMATIC");
signalfour();
}
else if (sec == 20) {
signalthree();
}
else if (sec == 10) {
signaltwo();
}
else if (sec == 0) {
signalone();
}
if (sec == 40) {
sec = 0;
}
}
BLYNK_WRITE(V1) {
 int button = param.asInt();
 if (button == 1) {
 iotsend=1;
 }
 else{iotsend=0;}
}