import json
import random
import math
import torch
from torch.utils.data import Dataset, DataLoader
from torch.optim import AdamW
from transformers import T5ForConditionalGeneration, T5Tokenizer, get_linear_schedule_with_warmup

class LayoutDataset(Dataset):
    def __init__(self, data, tokenizer):
        self.data = data
        self.tokenizer = tokenizer

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        item = self.data[idx]
        archetype = item.get("archetype", "process")
        count = item.get("item_count", 4)

        input_text = f"generate {archetype} layout: items={count}"

        W, H, margin = 12192000, 6858000, 1219200
        shapes = []

        if archetype == "funnel":
            for j in range(count):
                w = int((W - 2*margin) * (1 - j*0.15))
                shapes.append({"id": f"l{j}", "t": "trap", "x": margin + (W - 2*margin - w)//2, "y": margin + j*(H - 2*margin)//count, "w": w, "h": (H - 2*margin)//count})
        elif archetype == "cycle":
            r = min(W, H) // 3
            sz = min(W, H) // 6
            for j in range(count):
                ang = 2 * math.pi * j / count - math.pi / 2
                shapes.append({"id": f"n{j}", "t": "ellipse", "x": int(W//2 + r*math.cos(ang) - sz//2), "y": int(H//2 + r*math.sin(ang) - sz//2), "w": sz, "h": sz})
        else:
            sw = (W - 2*margin - (count-1)*margin//4) // count
            for j in range(count):
                shapes.append({"id": f"s{j}", "t": "rect", "x": margin + j*(sw + margin//4), "y": (H - H//3)//2, "w": sw, "h": H//3})

        output_text = json.dumps({"canvas": {"w": W, "h": H}, "shapes": shapes, "archetype": archetype}, separators=(",", ":"))

        inp_enc = self.tokenizer(input_text, max_length=128, padding="max_length", truncation=True, return_tensors="pt")
        out_enc = self.tokenizer(output_text, max_length=512, padding="max_length", truncation=True, return_tensors="pt")

        labels = out_enc["input_ids"].squeeze(0)
        labels[labels == self.tokenizer.pad_token_id] = -100

        return {
            "input_ids": inp_enc["input_ids"].squeeze(0),
            "attention_mask": inp_enc["attention_mask"].squeeze(0),
            "labels": labels
        }

def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")
    if device.type == "cuda":
        print(f"GPU: {torch.cuda.get_device_name(0)}")

    tokenizer = T5Tokenizer.from_pretrained("t5-base")
    model = T5ForConditionalGeneration.from_pretrained("t5-base").to(device)

    data = [json.loads(line) for line in open("intents.jsonl") if line.strip()]
    random.seed(42)
    random.shuffle(data)
    split = int(len(data) * 0.9)

    train_ds = LayoutDataset(data[:split], tokenizer)
    val_ds = LayoutDataset(data[split:], tokenizer)
    train_dl = DataLoader(train_ds, batch_size=16, shuffle=True)
    val_dl = DataLoader(val_ds, batch_size=16)

    optimizer = AdamW(model.parameters(), lr=3e-5)
    scheduler = get_linear_schedule_with_warmup(optimizer, 100, len(train_dl) * 10)

    print(f"Train: {len(train_ds)} Val: {len(val_ds)}")
    best_loss = float("inf")

    for epoch in range(10):
        model.train()
        total_loss = 0

        for i, batch in enumerate(train_dl):
            optimizer.zero_grad()
            outputs = model(
                input_ids=batch["input_ids"].to(device),
                attention_mask=batch["attention_mask"].to(device),
                labels=batch["labels"].to(device)
            )
            outputs.loss.backward()
            optimizer.step()
            scheduler.step()
            total_loss += outputs.loss.item()

            if (i + 1) % 5 == 0:
                print(f"Epoch {epoch+1} Batch {i+1}/{len(train_dl)} Loss: {outputs.loss.item():.4f}")

        model.eval()
        val_loss = 0
        with torch.no_grad():
            for batch in val_dl:
                outputs = model(
                    input_ids=batch["input_ids"].to(device),
                    attention_mask=batch["attention_mask"].to(device),
                    labels=batch["labels"].to(device)
                )
                val_loss += outputs.loss.item()

        val_loss /= len(val_dl)
        print(f"Epoch {epoch+1}: train_loss={total_loss/len(train_dl):.4f} val_loss={val_loss:.4f}")

        if val_loss < best_loss:
            best_loss = val_loss
            model.save_pretrained("model")
            tokenizer.save_pretrained("tokenizer")
            print(f"Saved best model! (val_loss={val_loss:.4f})")

    print(f"Training complete! Best val_loss: {best_loss:.4f}")

if __name__ == "__main__":
    main()
