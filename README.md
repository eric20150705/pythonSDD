# NEON CITY

這是一個使用 `pygame-ce` 製作的程式繪製 3D 自由拆樓沙盒遊戲。城市會在每次開始時隨機生成大量方塊大樓，玩家可以在第一人稱與第三人稱之間切換，持續把大樓拔出來。

## 執行

```powershell
python -m pip install -r requirements.txt
python game_3d.py
```

如果使用虛擬環境：

```powershell
.\.venv\Scripts\python.exe game_3d.py
```

## 操作

- `W` / `S`：前進／後退
- `A` / `D`：左右平移
- `Space`：跳躍
- 按住滑鼠右鍵拖曳：旋轉鏡頭
- 滑鼠滾輪：切換第一人稱／第三人稱
- 滑鼠左鍵：拆除游標指向的大樓
- `R`：重新隨機生成城市
- `Esc`：離開遊戲

遊戲使用 Pygame 的透視投影繪製方塊城市，不需要外部圖片、模型或其他 3D 引擎。`day1` 與 `day2` 目錄保留原本的 Pygame 練習。

## 邏輯測試

```powershell
python game_3d.py --self-test
python -m unittest discover -s tests -v
```
