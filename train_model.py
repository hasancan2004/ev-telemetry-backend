import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
import joblib

def train_ev_model():
    print("Veriler okunuyor ve yapay zeka antrenmana başlıyor...")
    
    # 1. Ders Kitabını (CSV) Oku
    df = pd.read_csv("ev_maintenance_data.csv")

    # 2. Sorular (X) ve Cevapları (y) Ayır
    X = df.drop("maintenance_required", axis=1) # Özellikler (Hız, Sıcaklık vs.)
    y = df["maintenance_required"]              # Hedef (Bozulur mu? 0 veya 1)

    # 3. Veriyi Böl (%80'i ile ders çalışacak, %20'si ile kendini test edecek)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # 4. Modeli Seç ve Eğit (Random Forest - 100 Karar Ağacı)
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)

    # 5. Sınav Vakti! Test verilerindeki başarı oranını ölçüyoruz
    predictions = model.predict(X_test)
    acc = accuracy_score(y_test, predictions)
    
    print("-" * 50)
    print(f"Model Başarı Oranı (Accuracy): %{acc * 100:.2f}")
    print("-" * 50)
    print("Detaylı Karne:")
    print(classification_report(y_test, predictions))

    # 6. Eğitilen Modeli Diske Kaydet (Hafızaya mühürlüyoruz)
    joblib.dump(model, "ev_health_model.pkl")
    print("\nMÜKEMMEL! Eğitilmiş zeki model 'ev_health_model.pkl' olarak kaydedildi.")

if __name__ == "__main__":
    train_ev_model()