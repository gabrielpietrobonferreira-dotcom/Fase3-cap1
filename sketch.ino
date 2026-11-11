/* FarmTech Fase 3 - coleta CSV. Mesmos pinos e regras da Fase 2.
   Cada ciclo de 2,1 segundos representa UMA HORA do modelo didatico.
   O estado registrado vale para [data_hora, data_hora + 1 hora).
   DHT22 mede umidade do ar; LDR simula pH; botoes NPK sao binarios.
   C = chuva prevista; S = sem chuva. Nao imprime alertas no CSV:
   eles sao representados pelas leituras e podem ser derivados depois.
*/
#include <DHT.h>
#include <time.h>
constexpr uint8_t PIN_DHT=4, PIN_RELE=5, PIN_N=12, PIN_P=13, PIN_K=14, PIN_LDR=34;
DHT dht(PIN_DHT, DHT22);
constexpr unsigned long INTERVALO_MS=2100;
unsigned long ultimaLeitura=0;
uint32_t ciclo=0;
bool chuva=false;
// 2026-01-01 00:00:00 UTC: origem ficticia do calendario simulado.
constexpr time_t INICIO=1767225600;

void setup() {
  Serial.begin(115200);
  pinMode(PIN_RELE, OUTPUT);
  digitalWrite(PIN_RELE, LOW);
  pinMode(PIN_N, INPUT_PULLUP);
  pinMode(PIN_P, INPUT_PULLUP);
  pinMode(PIN_K, INPUT_PULLUP);
  pinMode(PIN_LDR, INPUT);
  analogReadResolution(12);
  dht.begin();
  // simulado=0: coletado no Wokwi, embora todos os sensores sejam virtuais.
  // simulado=1 sera reservado a linhas adicionais geradas em Python.
  Serial.println("data_hora,umidade,ph,fosforo,potassio,bomba,simulado,nitrogenio,chuva_prevista");
}

void loop() {
  while (Serial.available()>0) {
    char c=Serial.read();
    if(c=='C'||c=='c') chuva=true;
    if(c=='S'||c=='s') chuva=false;
  }
  if(millis()-ultimaLeitura<INTERVALO_MS) return;
  ultimaLeitura=millis();
  float umidade=dht.readHumidity();
  float ph=analogRead(PIN_LDR)*14.0f/4095.0f;
  bool n=digitalRead(PIN_N)==LOW;
  bool p=digitalRead(PIN_P)==LOW;
  bool k=digitalRead(PIN_K)==LOW;
  // Falha de leitura desliga a bomba; pH e NPK nao bloqueiam irrigacao.
  bool bomba=!isnan(umidade) && umidade<50.0f && !chuva;
  digitalWrite(PIN_RELE,bomba ? HIGH : LOW);
  time_t instante=INICIO+static_cast<time_t>(ciclo)*3600;
  struct tm calendario;
  gmtime_r(&instante,&calendario);
  char data[20];
  strftime(data,sizeof(data),"%Y-%m-%d %H:%M:%S",&calendario);
  Serial.print(data);
  Serial.print(',');
  // Campo vazio representa falha, sem fabricar uma medicao.
  if(!isnan(umidade)) Serial.print(umidade,1);
  Serial.printf(",%.2f,%d,%d,%d,0,%d,%d\n",ph,p,k,bomba,n,chuva);
  ciclo++;
}
