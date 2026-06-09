import csv
import random

def generate_ev_data(num_samples=2000):
    data = []
    # Makine öğrenmesi modelimizin öğreneceği kolonlar (Sütunlar)
    headers = [
        "speed_kmh",
        "battery_level_pct",
        "regeneration_kw",
        "cabin_temperature_c",
        "tire_pressure_psi",
        "maintenance_required" # HEDEF KOLONUMUZ -> 0: Sağlıklı, 1: Arıza/Bakım Riski Var
    ]

    for _ in range(num_samples):
        # 1. Önce her şeyi "Normal" ve sağlıklı değerlerde üretiyoruz
        speed = random.randint(0, 120)
        battery = round(random.uniform(5.0, 100.0), 1)
        regen = round(random.uniform(0.0, 20.0), 1)
        temp = round(random.uniform(18.0, 28.0), 1)
        pressure = round(random.uniform(32.0, 36.0), 1)
        
        # Başlangıçta araba sapa sağlam kabul ediliyor
        maintenance = 0

        # 2. Şimdi yapay zekanın öğrenmesi için kasti "Arıza Senaryoları" yaratıyoruz
        anomaly_chance = random.random()

        # SENARYO 1: Kabin/Batarya Aşırı Isınması
        if anomaly_chance < 0.10:  # %10 ihtimalle bu senaryo gerçekleşir
            temp = round(random.uniform(35.0, 55.0), 1) # Sıcaklık 55'lere vurmuş
            maintenance = 1

        # SENARYO 2: Tehlikeli Sürüş (Düşük Lastik Basıncı + Yüksek Hız)
        elif anomaly_chance < 0.20:
            pressure = round(random.uniform(20.0, 28.0), 1) # Lastikler inik
            if speed > 90: # İnmiş lastikle 90'ı geçiyorsa risk çok yüksek!
                maintenance = 1

        # SENARYO 3: Batarya Zorlanması (Düşük Batarya + Aşırı Rejenerasyon)
        elif anomaly_chance < 0.25:
            battery = round(random.uniform(1.0, 10.0), 1) # Şarj bitmek üzere
            regen = round(random.uniform(30.0, 50.0), 1)  # Ama frene asılıp çok yükleniyor
            maintenance = 1

        # Ürettiğimiz bu 1 satırlık veriyi listeye ekliyoruz
        data.append([speed, battery, regen, temp, pressure, maintenance])

    # 3. Tüm veriyi CSV (Excel) dosyasına mühürlüyoruz
    with open("ev_maintenance_data.csv", mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(headers)
        writer.writerows(data)

    print(f"HARİKA! {num_samples} satırlık eğitim verisi başarıyla 'ev_maintenance_data.csv' dosyasına yazıldı.")

if __name__ == "__main__":
    # Yapay zekamız için tam 2000 satırlık dev bir ders kitabı üretiyoruz
    generate_ev_data(2000)