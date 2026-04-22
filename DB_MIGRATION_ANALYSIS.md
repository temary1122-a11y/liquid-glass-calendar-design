# 🔍 АНАЛИЗ МИГРАЦИИ НА SUPABASE СХЕМУ

## 📊 ТЕКУЩАЯ СИТУАЦИЯ

### Локальная схема (backend/database/db.py)
```python
class WorkDay(Base):
    id = Column(Integer, primary_key=True)
    day_date = Column(String(10), unique=True)
    is_closed = Column(Boolean, default=False)
    slots = relationship("TimeSlot", back_populates="work_day")

class TimeSlot(Base):
    id = Column(Integer, primary_key=True)
    day_id = Column(Integer, ForeignKey("work_days.id", ondelete="CASCADE"))  # ← PROBLEM
    time = Column(String(5))  # HH:MM
    is_booked = Column(Boolean, default=False)
    work_day = relationship("WorkDay", back_populates="slots")
    booking = relationship("Booking", back_populates="slot")

class Booking(Base):
    id = Column(Integer, primary_key=True)
    slot_id = Column(Integer, ForeignKey("time_slots.id", ondelete="CASCADE"), unique=True)  # ← PROBLEM
    user_id = Column(Integer, nullable=True)
    username = Column(String(255), nullable=True)
    client_name = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=True)
    status = Column(String(20), default="pending")
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    cancelled_at = Column(DateTime, nullable=True)
    cancellation_reason = Column(Text, nullable=True)
    slot = relationship("TimeSlot", back_populates="booking")
```

### Supabase схема (фактическая)
```sql
-- work_days
id (integer, NOT NULL)
day_date (text, NOT NULL)  -- YYYY-MM-DD
is_closed (integer, NOT NULL)  -- 0/1 вместо Boolean

-- time_slots
id (integer, NOT NULL)
day_date (text, NOT NULL)  -- ← NO ForeignKey, direct text field
slot_time (text, NOT NULL)  -- ← NO time field
is_booked (integer, NOT NULL)  -- 0/1 вместо Boolean

-- bookings
id (integer, NOT NULL)
user_id (integer, nullable)
username (text, nullable)
client_name (text, NOT NULL)
phone (text, NOT NULL)
day_date (text, NOT NULL)  -- ← NO slot_id, direct text field
slot_time (text, NOT NULL)  -- ← NO slot_id, direct text field
created_at (text, NOT NULL)  -- ISO format string
is_cancelled (integer, NOT NULL)  -- 0/1
cancel_reason (text, nullable)
cancelled_at (text, nullable)
service_id (text, nullable)
note (text, nullable)
status (text, NOT NULL)
```

## ⚠️ ПРОБЛЕМЫ

### 1. Foreign Keys vs Text Fields
- **Локально:** Foreign Keys (day_id, slot_id)
- **Supabase:** Text fields (day_date, slot_time)
- **Влияние:** SQLAlchemy ORM не может автоматически загружать relationships

### 2. Boolean vs Integer
- **Локально:** Boolean (is_closed, is_booked)
- **Supabase:** Integer (0/1)
- **Влияние:** Нужна конвертация при чтении/записи

### 3. DateTime vs Text
- **Локально:** DateTime (created_at, cancelled_at)
- **Supabase:** Text (ISO format string)
- **Влияние:** Нужна конвертация при чтении/записи

### 4. Field Names
- **Локально:** time (TimeSlot)
- **Supabase:** slot_time
- **Влияние:** Нужен alias или переименование

### 5. Missing Fields
- **Локально:** НЕТ is_cancelled, service_id
- **Supabase:** ЕСТЬ is_cancelled, service_id
- **Влияние:** Нужны дополнительные поля

## 🎋 ПЛАН ИЗМЕНЕНИЙ

### Шаг 1: Обновить backend/database/db.py

#### Изменения в WorkDay:
```python
# БЫЛО:
is_closed = Column(Boolean, default=False)

# СТАЛО:
is_closed = Column(Integer, default=0)  # 0 = False, 1 = True
```

#### Изменения в TimeSlot:
```python
# БЫЛО:
day_id = Column(Integer, ForeignKey("work_days.id", ondelete="CASCADE"))
time = Column(String(5), nullable=False)
is_booked = Column(Boolean, default=False)

# СТАЛО:
day_date = Column(String(10), nullable=False)  # YYYY-MM-DD
slot_time = Column(String(5), nullable=False)  # HH:MM
is_booked = Column(Integer, default=0)  # 0 = False, 1 = True

# УБРАТЬ relationships (будем загружать вручную)
```

#### Изменения в Booking:
```python
# БЫЛО:
slot_id = Column(Integer, ForeignKey("time_slots.id", ondelete="CASCADE"), unique=True)
created_at = Column(DateTime, default=datetime.utcnow)
cancelled_at = Column(DateTime, nullable=True)
cancellation_reason = Column(Text, nullable=True)

# СТАЛО:
day_date = Column(String(10), nullable=False)  # YYYY-MM-DD
slot_time = Column(String(5), nullable=False)  # HH:MM
created_at = Column(String, nullable=False)  # ISO format string
is_cancelled = Column(Integer, default=0)  # 0 = False, 1 = True
cancel_reason = Column(Text, nullable=True)  # renamed from cancellation_reason
cancelled_at = Column(String, nullable=True)  # ISO format string
service_id = Column(String(50), nullable=True)  # NEW field

# УБРАТЬ relationships (будем загружать вручную)
```

### Шаг 2: Обновить backend/api/routes/booking.py

#### Изменения в get_available_dates():
```python
# БЫЛО:
for slot in wd.slots:
    if not slot.is_booked:

# СТАЛО:
slots = db.query(TimeSlot).filter(TimeSlot.day_date == wd.day_date).all()
for slot in slots:
    if slot.is_booked == 0:  # Integer instead of Boolean
```

#### Изменения в create_booking():
```python
# БЫЛО:
slot = db.query(TimeSlot).filter(
    TimeSlot.day_id == work_day.id,
    TimeSlot.time == booking.time,
    TimeSlot.is_booked == False,
).first()

new_booking = Booking(
    slot_id=slot.id,
    ...
)

# СТАЛО:
slot = db.query(TimeSlot).filter(
    TimeSlot.day_date == booking.date,  # ← Changed
    TimeSlot.slot_time == booking.time,  # ← Changed
    TimeSlot.is_booked == 0,  # ← Integer
).first()

new_booking = Booking(
    day_date=booking.date,  # ← Changed
    slot_time=booking.time,  # ← Changed
    ...
)
```

### Шаг 3: Обновить backend/api/routes/admin.py

#### Изменения в get_work_days_with_bookings():
```python
# БЫЛО:
for slot in wd.slots:
    if slot.booking:
        b = slot.booking

# СТАЛО:
slots = db.query(TimeSlot).filter(TimeSlot.day_date == wd.day_date).all()
for slot in slots:
    booking = db.query(Booking).filter(
        Booking.day_date == slot.day_date,
        Booking.slot_time == slot.slot_time
    ).first()
```

#### Изменения в add_work_day():
```python
# БЫЛО:
new_wd = WorkDay(day_date=request.date, is_closed=False)
db.add(new_wd)
db.flush()
for t in request.time_slots:
    db.add(TimeSlot(day_id=new_wd.id, time=t))

# СТАЛО:
new_wd = WorkDay(day_date=request.date, is_closed=0)  # Integer
db.add(new_wd)
db.commit()  # Commit to get ID if needed
for t in request.time_slots:
    db.add(TimeSlot(day_date=request.date, slot_time=t, is_booked=0))
```

#### Изменения в add_time_slot():
```python
# БЫЛО:
existing = db.query(TimeSlot).filter(
    TimeSlot.day_id == work_day.id,
    TimeSlot.time == request.time,
).first()
db.add(TimeSlot(day_id=work_day.id, time=request.time))

# СТАЛО:
existing = db.query(TimeSlot).filter(
    TimeSlot.day_date == request.date,  # ← Changed
    TimeSlot.slot_time == request.time,  # ← Changed
).first()
db.add(TimeSlot(day_date=request.date, slot_time=request.time, is_booked=0))
```

#### Изменения в delete_time_slot():
```python
# БЫЛО:
slot = db.query(TimeSlot).filter(
    TimeSlot.day_id == work_day.id,
    TimeSlot.time == request.time,
).first()

# СТАЛО:
slot = db.query(TimeSlot).filter(
    TimeSlot.day_date == request.date,  # ← Changed
    TimeSlot.slot_time == request.time,  # ← Changed
).first()
```

#### Изменения в create_client():
```python
# БЫЛО:
slot = db.query(TimeSlot).filter(
    TimeSlot.day_id == work_day.id,
    TimeSlot.time == request.time,
    TimeSlot.is_booked == False,
).first()
booking = Booking(
    slot_id=slot.id,
    ...
)

# СТАЛО:
slot = db.query(TimeSlot).filter(
    TimeSlot.day_date == request.date,  # ← Changed
    TimeSlot.slot_time == request.time,  # ← Changed
    TimeSlot.is_booked == 0,  # ← Integer
).first()
booking = Booking(
    day_date=request.date,  # ← Changed
    slot_time=request.time,  # ← Changed
    ...
)
```

#### Изменения в update_client():
```python
# БЫЛО:
slot = db.query(TimeSlot).filter(
    TimeSlot.day_id == work_day.id,
    TimeSlot.time == request.time,
).first()
if slot.booking:
    slot.booking.client_name = request.name

# СТАЛО:
slot = db.query(TimeSlot).filter(
    TimeSlot.day_date == request.date,  # ← Changed
    TimeSlot.slot_time == request.time,  # ← Changed
).first()
booking = db.query(Booking).filter(
    Booking.day_date == slot.day_date,
    Booking.slot_time == slot.slot_time
).first()
if booking:
    booking.client_name = request.name
```

#### Изменения в delete_client():
```python
# БЫЛО:
slot = db.query(TimeSlot).filter(
    TimeSlot.day_id == work_day.id,
    TimeSlot.time == request.time,
).first()
if slot.booking:
    db.delete(slot.booking)
slot.is_booked = False

# СТАЛО:
slot = db.query(TimeSlot).filter(
    TimeSlot.day_date == request.date,  # ← Changed
    TimeSlot.slot_time == request.time,  # ← Changed
).first()
booking = db.query(Booking).filter(
    Booking.day_date == slot.day_date,
    Booking.slot_time == slot.slot_time
).first()
if booking:
    db.delete(booking)
slot.is_booked = 0  # Integer
```

### Шаг 4: Обновить backend/api/routes/profile.py

#### Изменения в get_user_bookings():
```python
# БЫЛО:
slot = b.slot
work_day = slot.work_day if slot else None
day_date=work_day.day_date if work_day else ""
slot_time=slot.time if slot else ""

# СТАЛО:
# Прямые поля из Booking
day_date=b.day_date
slot_time=b.slot_time
```

#### Изменения в cancel_booking():
```python
# БЫЛО:
slot = booking.slot
if slot:
    slot.is_booked = False
    work_day = slot.work_day

# СТАЛО:
# Найти слот по day_date и slot_time
slot = db.query(TimeSlot).filter(
    TimeSlot.day_date == booking.day_date,
    TimeSlot.slot_time == booking.slot_time
).first()
if slot:
    slot.is_booked = 0
```

## 📋 СПИСОК ФАЙЛОВ ДЛЯ ИЗМЕНЕНИЯ

1. ✅ backend/database/db.py - Обновить модели
2. ✅ backend/api/routes/booking.py - Обновить логику
3. ✅ backend/api/routes/admin.py - Обновить логику
4. ✅ backend/api/routes/profile.py - Обновить логику

## ⚠️ РИСКИ

1. **Потеря данных:** НЕТ - мы не изменяем Supabase схему
2. **Несоответствие типов:** Boolean → Integer конвертация
3. **Отсутствие relationships:** Нужно загружать данные вручную
4. **DateTime конвертация:** String ↔ DateTime при чтении/записи

## ✅ ПРЕИМУЩЕСТВА

1. Сохранить существующие данные в Supabase
2. Нет миграции базы данных
3. Проще в реализации
4. Меньше риска

## 🎯 ПОРЯДОК ВНЕДРЕНИЯ

1. Обновить db.py
2. Обновить booking.py
3. Обновить admin.py
4. Обновить profile.py
5. Протестировать локально
6. Задеплоить на Render
7. Проверить в продакшне
