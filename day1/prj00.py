###################################定義含式區#############################
# 沒有輸入直，沒有返回值
def show_message():
    print("開始複習 function!")
# 有輸入值，沒有返回值
def show_name(name):
    print(f"你好", name)
# 有輸入值，有返回值
def add_numbers(number1, number2):
    return number1 + number2
#####################################主程式#########################

#呼叫沒有輸入值的含式
show_message()

#傳入不同的名子

show_name("小傻逼")
show_name("大傻逼")

#把返回值存入變數
answer = add_numbers(7, 80)
print(f"答案:{answer}")