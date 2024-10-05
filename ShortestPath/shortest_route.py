import heapq
import time

def main(yolo_data_queue, car_number_data_queue, route_data_queue, event):

    init(yolo_data_queue)

    event.set()

    roop(yolo_data_queue, car_number_data_queue, route_data_queue)

# 최초 주차된 차량 아이디 부여
def init(yolo_data_queue):
    tracking_data = yolo_data_queue.get()["vehicles"]

    print(tracking_data)
    print(tracking_data[1])

    for key, value in tracking_data.items():
        print(key)
        print(value)
        car_number = input(f"id {key}번 차량 번호: ")
        set_car_numbers[car_number] = value["position"]

def roop(yolo_data_queue, car_number_data_queue, route_data_queue):
    """차량 추적 데이터와 차량 번호 데이터를 받아오는 메인 함수"""

    print(set_car_numbers)
    while True:
        # 큐에서 데이터 가져오기
        tracking_data = yolo_data_queue.get()
        if tracking_data is None:  # 종료 신호 (None) 받으면 종료
            break

        # 데이터 처리
        vehicles = tracking_data["vehicles"]

        print(vehicles)

        # 최초 실행의 경우 주차된 차량 아이디 부여
        if isFirst:
            isFirst_func(vehicles)

        parking_positions = {}  # 주차한 차량의 위치 정보 {구역 아이디: 차량 아이디}
        walking_positions = {}  # 이동 중인 차량의 위치 정보 {구역 아이디: 차량 아이디}

        print(parking_positions)

        for car_id, value in vehicles.items():
            check_position(car_id, value, parking_positions, walking_positions)

        set_parking_space(parking_positions)
        set_walking_space(walking_positions)

        # 주차 구역 차량 시간 기록 또는 주차 처리
        for key, value in parking_positions.items():
            vehicle_parking_time(key, value)

        if 1 in walking_positions:
            print("입차 하는 차량이 있습니다.")
            if car_number_data_queue.qsize() > 0:
                car_number = car_number_data_queue.get()
                print(f"2번 쓰레드: 라즈베리 파이로부터 수신한 차량 번호: {car_number}")
                car_numbers[walking_positions[1]] = {"car_number": car_number, "status": "entry", "parking": set_goal(car_number), "route": []}
                print(car_numbers)

        vehicles_to_route = {}  # 경로를 계산할 차량

        # 이동 구역에 있는 차량이 경로가 없는 경우 또는 경로에서 벗어난 경우
        for key, value in walking_positions.items():
            vehicle_moving(key) # 주차 시간 삭제
            temp_route = car_numbers[value]["route"]
            if value in car_numbers and car_numbers[value]["status"] == "entry" and (not temp_route or key not in temp_route):
                decrease_congestion(temp_route)
                car_numbers[value]["route"] = []
                vehicles_to_route[key] = value

            # 주차 후 출구로 이동하는 경우
            elif value in car_numbers and car_numbers[value]["status"] == "parking" and (not temp_route or key not in temp_route):
                decrease_congestion(temp_route)
                car_numbers[value]["route"] = []    # 경로 비우기
                parking_space[car_numbers[value]["parking"]]["status"] = "empty"    # 주차 공간 비우기
                car_numbers[value]["parking"] = -1  # 출구로 설정
                vehicles_to_route[key] = value

            # 차량이 경로를 따라 가고 있는 경우
            elif value in car_numbers and key in temp_route:
                temp_index = temp_route.index(key)  # 경로 상에서 현재 위치의 인덱스
                # 경로의 첫번째 위치면 스킵
                if temp_index == 0:
                    continue
                decrease_congestion_target_in_route(temp_route, key)
                car_numbers[value]["route"] = temp_route[temp_index:]    # 경로 수정


        print("경로 계산할 차량 ", vehicles_to_route)

        # 경로를 계산할 차량이 있는 경우 - 이동 중인 차량의 경로 계산
        for key, value in vehicles_to_route.items():
            parking_goal = get_walking_space_for_parking_space(car_numbers[value]["parking"])
            print("경로 계산", key, parking_goal)
            route = a_star(graph, congestion, key, parking_goal)
            amend_goal, amend_parking_space = check_route(route[:-1])

            # 경로 상에 비어있는 주차 공간이 있는 경우 경로 및 주차 공간 변경
            if amend_goal is not None:
                route = route[:route.index(amend_goal) + 1]
                parking_space[car_numbers[value]["parking"]]["status"] = "empty"    # 이전 주차 공간 비우기
                # car_numbers[walking_positions[key]]["parking"] = amend_parking_space
                car_numbers[value]["parking"] = amend_parking_space # 추자 공간 변경

            print(route)
            increase_congestion(route)
            car_numbers[value]["route"] = route


        print("주차한 차량: ", parking_positions)
        print("이동 중인 차량: ", walking_positions)
        print(car_numbers)

        print(parking_space)
        print(congestion)

        # 차량 데이터 전송
        route_data_queue.put({"total_cars": number_of_parking_space, "cars": car_numbers})

        yolo_data_queue.task_done()  # 처리 완료 신호


# 경로 내의 특정 구역까지의 혼잡도를 감소시키는 함수
def decrease_congestion_target_in_route(arg_route, arg_target):
    """경로 내의 특정 구역까지의 혼잡도를 감소시키는 함수"""
    for node in arg_route:
        if node == arg_target:
            break
        for next_node in congestion[node]:
            congestion[node][next_node] -= 2

# 차량이 주차 구역에 들어온 시간을 기록하는 함수
def vehicle_parking_time(arg_space, arg_vehicle_id):
    """차량이 주차 구역에 들어온 시간을 기록하는 함수"""

    # 주차 구역에 처음 들어온 경우 (이전 시간이 없는 경우)
    if arg_vehicle_id not in stop_times:
        stop_times[arg_vehicle_id] = time.time()
    else:
        # 주차 구역에 처음 들어온 시간이 있고, 5초 이상 경과한 경우
        if time.time() - stop_times[arg_vehicle_id] >= 5:
            car_numbers[arg_vehicle_id]["status"] = "parking"
            car_numbers[arg_vehicle_id]["parking_time"] = stop_times[arg_vehicle_id]
            parking_space[car_numbers[arg_vehicle_id]["parking"]]["status"] = "empty"   # 데이터의 무결성을 위해 우선 비움
            car_numbers[arg_vehicle_id]["parking"] = arg_space
            car_numbers[arg_vehicle_id]["route"] = []   # 주차 시 경로 초기화
            parking_space[arg_space]["status"] = "occupied"

# 사전에 주차 되어 있던 차량에 번호 부여
def isFirst_func(arg_vehicles):
    """사전에 주차 되어 있던 차량에 번호 부여"""
    print("isFirst", arg_vehicles)
    print("isFirst", set_car_numbers)
    global isFirst
    for key, value in set_car_numbers.items():
        for car_id, car_value in arg_vehicles.items():
            # 오차 범위 +- 30 이내 이면 같은 차량으로 판단
            if value[0] - 20 <= car_value["position"][0] <= value[0] + 20 and \
                    value[1] - 20 <= car_value["position"][1] <= value[1] + 20:
                car_numbers[car_id] = {"car_number": key, "status": "entry", "parking": set_goal(key), "route": []}
                print("isFirst", car_numbers)
                break

    isFirst = False

# 차량이 이동 중인 경우
def vehicle_moving(arg_vehicle_id):
    if arg_vehicle_id in stop_times:
        del stop_times[arg_vehicle_id]

# 경로 내의 구역의 혼잡도를 감소시키는 함수
def decrease_congestion(arg_route):
    """경로 내의 구역의 혼잡도를 감소시키는 함수"""
    for node in arg_route:
        for next_node in congestion[node]:
            congestion[node][next_node] -= 2

# 경로 내의 구역의 혼잡도를 증가시키는 함수
def increase_congestion(arg_route):
    """경로 내의 구역의 혼잡도를 증가시키는 함수"""
    for node in arg_route:
        for next_node in congestion[node]:
            congestion[node][next_node] += 2

# 경로상에 추차할 구역이 있는지 확인하는 함수
def check_route(arg_route):
    for walking_space_id in arg_route:
        for parking_space_id in walking_space[walking_space_id]["parking_space"]:
            if parking_space[parking_space_id]["status"] == "empty":
                parking_space[parking_space_id]["status"] = "target"
                parking_space[parking_space_id]["car_number"] = walking_space[walking_space_id]["car_number"]
                return walking_space_id, parking_space_id

    return None, None

# 주차 구역에 대한 이동 구역을 반환하는 함수
def get_walking_space_for_parking_space(arg_parking_space):
    """주차 구역에 대한 이동 구역을 반환하는 함수"""
    for key, value in walking_space.items():
        if arg_parking_space in tuple(value["parking_space"]):
            return key

# 차량의 위치를 확인하는 함수
def check_position(vehicle_id, vehicle_value, arg_parking_positions, arg_walking_positions):
    """차량의 위치를 확인하는 함수"""
    print("vhhicle", vehicle_id, vehicle_value)
    for key, value in parking_space.items():
        if value["position"][0][0] <= vehicle_value["position"][0] <= value["position"][1][0]\
        and value["position"][0][1] <= vehicle_value["position"][1] <= value["position"][1][1]:
            arg_parking_positions[key] = vehicle_id
            return

    for key, value in walking_space.items():
        if value["position"][0][0] <= vehicle_value["position"][0] <= value["position"][1][0]\
        and value["position"][0][1] <= vehicle_value["position"][1] <= value["position"][1][1]:
            arg_walking_positions[key] = vehicle_id
            return

# 주차 공간을 설정하는 함수
def set_parking_space(arg_parking_positions):
    """주차 공간을 설정하는 함수"""
    for key, value in parking_space.items():
        if value["name"] in arg_parking_positions:
            parking_space[key]["status"] = "occupied"
            parking_space[key]["car_number"] = arg_parking_positions[value["name"]]
        elif value["status"] == "target":
            pass
        # else:
        #     parking_space[key]["status"] = "empty"
        #     parking_space[key]["car_number"] = None

# 이동 공간을 설정하는 함수
def set_walking_space(arg_walking_positions):
    """이동 공간을 설정하는 함수"""
    for key, value in walking_space.items():
        if value["name"] in arg_walking_positions:
            walking_space[key]["status"] = "occupied"
            walking_space[key]["car_number"] = arg_walking_positions[value["name"]]
        else:
            walking_space[key]["status"] = "empty"
            walking_space[key]["car_number"] = None

# 주차할 공간을 지정하는 함수 (할당할 주차 공간의 순서 지정)
def set_goal(arg_car_number):
    """주차할 공간을 지정하는 함수"""
    for i in (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21):    # 할당할 주차 구역 순서
        if parking_space[i]["status"] == "empty":
            parking_space[i]["status"] = "target"
            parking_space[i]["car_number"] = arg_car_number
            return i

# A* 알고리즘
def heuristic(a, b):
    # 휴리스틱 함수: 여기서는 간단하게 두 노드 간 차이만 계산 (유클리드 거리는 필요하지 않음)
    # 예측용 함수로 모든 계산을 하기 전에 대략적인 예측을 하여 가능성 높은곳만 계산하도록 도와줌
    return 0

# A* 알고리즘
def a_star(graph, congestion, start, goal):
    """경로를 계산하여 반환하는 함수"""
    pq = []
    heapq.heappush(pq, (0, start))
    came_from = {start: None}
    cost_so_far = {start: 0}
    
    while pq:
        current = heapq.heappop(pq)[1]
        
        if current == goal:
            break
        
        for next_node in graph[current]:
            new_cost = cost_so_far[current] + graph[current][next_node] + congestion[current][next_node]
            if next_node not in cost_so_far or new_cost < cost_so_far[next_node]:
                cost_so_far[next_node] = new_cost
                priority = new_cost + heuristic(goal, next_node)
                heapq.heappush(pq, (priority, next_node))
                came_from[next_node] = current
    
    # 경로를 역추적하여 반환
    current = goal
    path = []
    while current:
        path.append(current)
        current = came_from[current]
    path.reverse()
    
    return path

# 주차 구역의 좌표값
parking_space = {
    # status = empty, occupied, target
    0: {"name": "A1", "status": "empty", "car_number": None, "position": ((75, 0), (100, 50))},
    1: {"name": "A2", "status": "empty", "car_number": None, "position": ((100, 0), (117, 50))},
    2: {"name": "A3", "status": "empty", "car_number": None, "position": ((117, 0), (134, 50))},
    3: {"name": "A4", "status": "empty", "car_number": None, "position": ((134, 0), (150, 50))},
    4: {"name": "A5", "status": "empty", "car_number": None, "position": ((150, 0), (175, 50))},
    5: {"name": "A6", "status": "empty", "car_number": None, "position": ((175, 0), (200, 50))},
    6: {"name": "B1", "status": "empty", "car_number": None, "position": ((100, 100), (125, 125))},
    7: {"name": "B2", "status": "empty", "car_number": None, "position": ((100, 125), (125, 150))},
    8: {"name": "B3", "status": "empty", "car_number": None, "position": ((125, 100), (150, 125))},
    9: {"name": "B4", "status": "empty", "car_number": None, "position": ((125, 125), (150, 150))},
    10: {"name": "C1", "status": "empty", "car_number": None, "position": ((100, 200), (125, 225))},
    11: {"name": "C2", "status": "empty", "car_number": None, "position": ((100, 225), (125, 250))},
    12: {"name": "C3", "status": "empty", "car_number": None, "position": ((125, 200), (150, 225))},
    13: {"name": "C4", "status": "empty", "car_number": None, "position": ((125, 225), (150, 250))},
    14: {"name": "D1", "status": "empty", "car_number": None, "position": ((200, 75), (250, 100))},
    15: {"name": "D2", "status": "empty", "car_number": None, "position": ((200, 100), (250, 125))},
    16: {"name": "D3", "status": "empty", "car_number": None, "position": ((200, 125), (250, 150))},
    17: {"name": "D4", "status": "empty", "car_number": None, "position": ((200, 150), (250, 175))},
    18: {"name": "D5", "status": "empty", "car_number": None, "position": ((200, 175), (250, 200))},
    19: {"name": "D6", "status": "empty", "car_number": None, "position": ((200, 200), (250, 225))},
    20: {"name": "D7", "status": "empty", "car_number": None, "position": ((200, 225), (250, 250))},
    21: {"name": "D8", "status": "empty", "car_number": None, "position": ((200, 250), (250, 275))},
    # 테스트 값
    22: {"name": "TEST", "status": "empty", "car_number": None, "position": ((1200, 600), (1300, 700))},
    23: {"name": "TEST", "status": "empty", "car_number": None, "position": ((1800, 200), (1900, 300))},
}

# 이동 구역의 좌표값
walking_space = {
    1: {"name": "Entry", "position": ((0, 50), (50, 100)), "parking_space": ()},
    2: {"name": "Path_2", "position": ((50, 50), (100, 100)), "parking_space": (0, )},
    3: {"name": "Path_3", "position": ((100, 50), (150, 100)), "parking_space": (1, 2, 3)},
    4: {"name": "Path_4", "position": ((150, 50), (200, 100)), "parking_space": (4, 5, 14)},
    5: {"name": "Path_5", "position": ((50, 100), (100, 150)), "parking_space": (6, 7)},
    6: {"name": "Path_6", "position": ((150, 100), (200, 150)), "parking_space": (8, 9, 15, 16)},
    7: {"name": "Path_7", "position": ((50, 150), (100, 200)), "parking_space": ()},
    8: {"name": "Path_8", "position": ((100, 150), (150, 200)), "parking_space": ()},
    9: {"name": "Path_9", "position": ((150, 150), (200, 200)), "parking_space": (17, 18)},
    10: {"name": "Path_10", "position": ((50, 200), (100, 250)), "parking_space": (10, 11)},
    11: {"name": "Path_11", "position": ((150, 200), (200, 250)), "parking_space": (12, 13, 19, 20)},
    12: {"name": "Path_12", "position": ((50, 250), (100, 300)), "parking_space": ()},
    13: {"name": "Path_13", "position": ((100, 250), (150, 300)), "parking_space": ()},
    14: {"name": "Path_14", "position": ((150, 250), (200, 300)), "parking_space": (21, )},
    15: {"name": "Exit", "position": ((0, 250), (50, 300)), "parking_space": (-1, )},   # 출구
    # 테스트 값
    16: {"name": "TEST", "position": ((800, 300), (850, 350)), "parking_space": (22, )},
    17: {"name": "TEST", "position": ((850, 300), (900, 350)), "parking_space": (23, )},
}

# 그래프
graph = {
    1: {2: 1},
    2: {1: 1, 3: 1, 5: 1},
    3: {2: 2, 4: 1},
    4: {3: 1, 6: 1},
    5: {2: 2, 7: 1},
    6: {4: 1, 9: 1},
    7: {5: 1, 8: 1, 10: 1},
    8: {7: 1, 9: 1},
    9: {6: 1, 8: 1, 11: 1},
    10: {7: 1, 12: 1},
    11: {9: 1, 14: 1},
    12: {10: 1, 13: 1, 15: 1},
    13: {12: 1, 14: 1},
    14: {11: 1, 13: 1},
    15: {12: 1}
}

# 혼잡도
congestion = {
    1: {2: 1},
    2: {1: 1, 3: 1, 5: 1},
    3: {2: 2, 4: 1},
    4: {3: 1, 6: 1},
    5: {2: 2, 7: 1},
    6: {4: 1, 9: 1},
    7: {5: 1, 8: 1, 10: 1},
    8: {7: 1, 9: 1},
    9: {6: 1, 8: 1, 11: 1},
    10: {7: 1, 12: 1},
    11: {9: 1, 14: 1},
    12: {10: 1, 13: 1, 15: 1},
    13: {12: 1, 14: 1},
    14: {11: 1, 13: 1},
    15: {12: 1}
}

# 차량의 번호와 ID를 매핑
car_numbers = {
    # status = entry, parking, exit
    # parking = 상태가 entry일 경우에는 주차할 구역, parking일 경우에는 주차한 구역
    # id: {"car_number": "1234", "status": "entry", "parking": 0}
    # 0: {"car_number": "12가1234", "status": "entry", "parking": 21, "route": [], "parking_time": None},
}

# 경로
routes = {}

# 각 차량의 정지 시간을 기록
stop_times = {}

# 입구의 좌표
entry_x = (0, 100)
entry_y = (0, 100)

# 이미 주차되어 있던 차량
set_car_numbers = {}

isFirst = True

number_of_parking_space = len(parking_space)

if __name__ == "__main__":

    start = 0
    goal = 14

    path = a_star(graph, congestion, start, goal)
    print(path)