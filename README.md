# SCIST_Bot

For SCIST 2025 寒訓

有個 requirements.txt
裡面放必要環境表（不要把整個虛擬環境丟上來）
用來下載（如想開 venv 請先開後在 install）

```
pip install -r requirements.txt
```

如要產生新的

```
pip freeze > requirements.txt
```

---

# 需要的功能

狼人殺(其他沒說的都寫在 hackmd 裡面了 這裡寫重要的)  
一組有 7 平民+2 狼人  
!!他們一組不會互殺 同組同陣線!!  
每個玩家 6 個號碼(四位數) 也等於 6 條命  
狼誰都可以殺  
當"全部的狼人"殺 5 人後開投票  
投票系統

計分系統{  
活動需求  
狼人殺  
待新增...  
}

# 已完成的功能

emoji 已導入  
可以用`self.emoji = self.bot.emoji`導入  
`{self.emoji['XXX']}`調用

計分系統{  
加分、分數板(有動圖)
}

提升一部分文字的美觀(?  
加個 emoji 而已

# Error

test
