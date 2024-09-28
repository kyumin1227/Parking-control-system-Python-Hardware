import threading
import time
import queue
import yolo_tracking as yolo
import shortest_route as sr
import uart

# 프로그램 종료 플래그
stop_event = threading.Event()

# 공유할 데이터 큐
yolo_data_queue = queue.Queue()
car_number_data_queue = queue.Queue()

# 4. 경로를 서버와 Arduino로 전송 (무한 반복)
def send_path_to_server_and_arduino():
    while not stop_event.is_set():
        # print("경로를 서버와 Arduino로 전송 중...")
        time.sleep(5)

# 쓰레드 생성
thread1 = threading.Thread(target=yolo.track_vehicles, kwargs={"yolo_data_queue": yolo_data_queue})
thread2 = threading.Thread(target=sr.calculate_optimal_path, kwargs={"yolo_data_queue": yolo_data_queue, "car_number_data_queue": car_number_data_queue})
thread3 = threading.Thread(target=uart.get_car_number, kwargs={"car_number_data_queue": car_number_data_queue})
thread4 = threading.Thread(target=send_path_to_server_and_arduino)

# 쓰레드 시작
thread1.start()
thread2.start()
thread3.start()
thread4.start()

try:
    # 메인 프로그램을 무한 대기 상태로 유지
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    # 키보드 인터럽트 발생 시 쓰레드 종료
    print("프로그램 종료 중...")
    stop_event.set()

# 모든 쓰레드가 종료될 때까지 대기
thread1.join()
thread2.join()
thread3.join()
thread4.join()

print("프로그램이 정상적으로 종료되었습니다.")
