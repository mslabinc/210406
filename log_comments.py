import serial, sys, queue
import re, time
#from pylab import *
from threading import (Event, Thread)
import RPi.GPIO as GPIO

global M 



"""
{210322}
月曜、火曜で
FLiNaKの調整に（200C, 400Cの真空引きで）成功

{210202}
MTC金属技研、片山ラボ
＞＞
熱電対の位置
１salt の中
２body
３底
４フランジ
"""

"""
{210201}
１）温度が上がると、熱が逃げるので、その分を補填して温度上昇を一定に保つとすると、どうなるか？
２）ギャップがあって、温度が上がりにくい場合は、外側の温度でどのように制御するか？
　　（内側にギャップが有る）　
"""


"""
{210122}
＠九州大学、Ajiさんと。
packet_write_wait: Connection to 192.168.150.98 port 22: Broken pipe
"""


s8="""{210117}
加熱試験を実施した。
問題点は加熱方法。サインカーブで5サイクル位の間を
10段階に分けてスイッチングするような手法を考えたい。
時間にすると0.1秒になる。
一方で電流の計測を平均することができると良いのだが。
"""

s7="""
{210117}
M5から流れてくる、unicodeで、先頭でエラーを起こす。
02,16:07:36.7,11.5000,10.1875,10.5625,11.1250,0.0000,10.8125,11.0625,10.6250,11.3125,11.3750
 /home/pi/Arduino/sketch_M5SSMCP9600OCT22_02/sketch_M5SSMCP9600OCT22_02.ino139 error code =-2

Debug0,in temp.reader line_s = ['\x0002', '12:44:49.0', '14.0625', '14.1250', '14.2500', '14.1875', '14.1875', '16.3750', '16.0625', '15.6875', '15.5625', '15.5625\r\n']
"""


S6="""
{210116}
tc_queue_dict
これの使い方がわからない。使ってるのかな?
＞＞
別の話だけど
ssr_group_dictなどと言うグループ化を考えたので
ややこしくなってしまった
"""

S5="""
{200913}
read_serial02d_x200815_1（Tcを読む、木下が変更）から
HNGN90_chibaf_4ced3_200517_copy.py（千葉さん）から
改造
"""


s3="""
{201018A}
ls /dev/*USB*
(Mac)tty.SLAB_USBtoUART
(Raspberrypi)TTYUSB0 
"""

s4="""
{201018B}
M is fraction of on-time in 60 or 50 Hz cycle
  0<=M<=11, M=0 is off
  M=11 is full-time on
  >> 
  for 50 Hz area;
    time.sleep(0.1/10/2)
    zero-cross point is 100 times in one second 
    so that divide by 2
    (0, pi) is devided by 10 and set level of power.
  >>
"""


s1="""
ls /dev/usb*  でM5のつながっているポートを探して同定。
Python (出力ファイル名)　（port名）　で起動
>>


{200815_1}
（threadingを使用）
read_serial02d_x200815_1.py
read_serial02d_x200814_6.py

Threadで読み込みの並列化をして
Eventの、wait,   set/clear
Queueの、put/get
などが少し使えるようになった。
event.clear()　#フラグを false にして止める
これで両方のthreadからアウトプットが連続的に出るようになった。


>>
{200812}
UARTのバッファA=ser.in_waitingを監視した。
200812_2ではf.write(",".join(line_s))に異常が見られない
しかし、print(A,B,line_s)では
800を越えると、
UARTのバッファに92が出てくる。たまに^[[B92とか雑音？が入る
>>
{200812-2}
バッファに溜まっている数：in_waitingを監視している。
92 or 0 に留まる処まで持ってこれた。

>>
{200813}
Thread間のデータのやり取りに、
Queueを使ってみたい。

"""
s2="""set()
内部フラグの値を true にセットします。フラグの値が true になるのを待っている全てのスレッドを起こします。一旦フラグが true になると、スレッドが wait() を呼び出しても全くブロックしなくなります。

clear()
内部フラグの値を false にリセットします。以降は、 set() を呼び出して再び内部フラグの値を true にセットするまで、 wait() を呼び出したスレッドはブロックするようになります。

wait(timeout=None)
内部フラグの値が true になるまでブロックします。 wait() 処理に入った時点で内部フラグの値が true であれば、直ちに処理を戻します。そうでない場合、他のスレッドが set() を呼び出してフラグの値を true にセットするか、オプションのタイムアウトが発生するまでブロックします。
"""




def port_read():
  ser.reset_input_buffer
  line_byte = ser.readline()  #一回、読み飛ばしをかける
  #一回バッファークリアしないといけない？？？
  ser.reset_input_buffer
  time.sleep(0.2)
  while True:
    try:
      A=ser.in_waiting
      if (ser.in_waiting)>0:
        line_byte = ser.readline()
        q.put(line_byte)
        if False :
          print(A,q.qsize(),line_byte)
          #(q.qsize(),"=queue_size")
        event.wait()
    except KeyboardInterrupt:
      print ('exiting thread-1 in port_read')
      sys.exit


def SSR():
  
  led_pin1 = 2
  led_pin2 = 3
  led_pin3 = 4
  led_pin4 = 9
  led_pin5 = 10
  led_pin6 = 11

  GPIO.cleanup()

  GPIO.setmode(GPIO.BCM)
  GPIO.setup(led_pin1, GPIO.OUT)
  GPIO.setup(led_pin2, GPIO.OUT)
  GPIO.setup(led_pin3, GPIO.OUT)
  GPIO.setup(led_pin4, GPIO.OUT)
  GPIO.setup(led_pin5, GPIO.OUT)
  GPIO.setup(led_pin6, GPIO.OUT)


  M1=0   #   0<=M1<=11, M1=0 is off, M1=11 is full-time on for 50 heltz region.
  M2=0
  M3=0
  M4=0
  M5=0
  M6=0
        
  while True:
    N=0    #   COUNTER at AC voltage angle of 0 to pi, pi to 2*pi, .....
    M=q2.get()
    for j in range(10):
      N+=1
      if M>=N: 
        GPIO.output(led_pin1, True)
        GPIO.output(led_pin2, True)
        GPIO.output(led_pin3, True)
        GPIO.output(led_pin4, True)
        GPIO.output(led_pin5, True)
        GPIO.output(led_pin6, True)
        #print("+++++true+++++")
      time.sleep(0.1/10/2)
      if M<N:
        GPIO.output(led_pin1, False)
        GPIO.output(led_pin2, False)
        GPIO.output(led_pin3, False)
        GPIO.output(led_pin4, False)
        GPIO.output(led_pin5, False)
        GPIO.output(led_pin6, False)
        #print("-----false-----")
      time.sleep(0.1/10/2)
      #print("N=",N)
      print("SSR_M=",M)  


def Control():
  time.sleep(0.2)
  event.set()#フラグを true にして起動
  time.sleep(3)
  if False :      #debug
    event.clear() #フラグを false にして止める
  time.sleep(1)
  print("plotting now")
   
  
  while True:
    line_byte=q.get()
    #print(q.qsize(),"line_byte",line_byte)
    line=line_byte.decode(encoding='utf-8')
    
    #line=line.replace("\x000","")
    line_s=line.split(',')  # list of numbers(character) separated by "," 
    f.write(",".join(line_s))
    line_p=str(line).replace("\r\n","")
    print("line_s=",line_s) 
    T_meas=float(line_s[2])  # temperature is from float(line_s[3???]).  coreresponds to Tc-1.
    print("float(line_s[2])=",float(line_s[2]))   # <== {read_serial02d_x200913_1.py debug print}
    s_work="""
    T_measは、Tc-1なので、これをPIDの計測値としてPID制御をする。
    """
    T_target= 200
    # print("T_meas=", T_meas)
    # print("T_target-T_meas=",T_target-T_meas)
    M= round( (T_target-T_meas)/10 )  #test for control  {201018}
    print("control_M=",M)
    q2.put(M)
  
#     time.sleep(1)

event=Event()
q = queue.Queue()
q2 = queue.LifoQueue()
M = 1 

strPort = sys.argv[2]   # serial port
ser=serial.Serial(strPort,115200,timeout=0) #20200627 115200->19200
ser.send_break()
ser.reset_input_buffer
ser.reset_input_buffer
ser.reset_input_buffer
ser.reset_input_buffer
#何回もリセットするとin_waitingの数が減る。
#スリープさせるとin_waitingの数が増えてくる。
print("connected to: " + ser.portstr)

file=sys.argv[1]  # file name
regex = re.compile('\d+')  # for extracting number from strings
f=open(file,"w+")
y=[0]*100
data=[];itime=0

thread1 = Thread(target=port_read)
thread2 = Thread(target=Control)
thread3 = Thread(target=SSR)

thread1.start()
time.sleep(3)
thread2.start()
time.sleep(3)
thread3.start()


thread1.join()
print ('exiting at thread1.join')
ser.close()
f.close()

#thread2.start()


ser.reset_input_buffer
ser.close()
f.close()
