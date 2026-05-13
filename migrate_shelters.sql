USE AnimalShelterDB;
GO

-- 1. Создаем таблицу приютов (Shelters)
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'Shelters')
BEGIN
    CREATE TABLE Shelters (
        ShelterID INT PRIMARY KEY IDENTITY(1,1),
        ShelterName NVARCHAR(100) NOT NULL UNIQUE CHECK (ShelterName <> ''),
        Address NVARCHAR(255) NULL,
        Phone NVARCHAR(20) NULL,
        Email NVARCHAR(100) NULL,
        Description NVARCHAR(MAX) NULL,
        IsActive BIT NOT NULL DEFAULT 1,
        CreatedDate DATETIME NOT NULL DEFAULT GETDATE()
    );
    PRINT 'Таблица Shelters создана';
END
ELSE
BEGIN
    PRINT 'Таблица Shelters уже существует';
END
GO

-- 2. Добавляем поле ShelterID в таблицу Animals
IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('Animals') AND name = 'ShelterID')
BEGIN
    ALTER TABLE Animals ADD ShelterID INT NULL;
    PRINT 'Поле ShelterID добавлено в таблицу Animals';
END
ELSE
BEGIN
    PRINT 'Поле ShelterID уже существует в таблице Animals';
END
GO

-- 3. Добавляем внешний ключ для Animals.ShelterID
IF NOT EXISTS (SELECT * FROM sys.foreign_keys WHERE name = 'FK_Animals_Shelters')
BEGIN
    ALTER TABLE Animals
    ADD CONSTRAINT FK_Animals_Shelters
    FOREIGN KEY (ShelterID) REFERENCES Shelters(ShelterID);
    PRINT 'Внешний ключ FK_Animals_Shelters добавлен';
END
ELSE
BEGIN
    PRINT 'Внешний ключ FK_Animals_Shelters уже существует';
END
GO

-- 4. Добавляем поле ShelterID в таблицу News
IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('News') AND name = 'ShelterID')
BEGIN
    ALTER TABLE News ADD ShelterID INT NULL;
    PRINT 'Поле ShelterID добавлено в таблицу News';
END
ELSE
BEGIN
    PRINT 'Поле ShelterID уже существует в таблице News';
END
GO

-- 5. Добавляем внешний ключ для News.ShelterID
IF NOT EXISTS (SELECT * FROM sys.foreign_keys WHERE name = 'FK_News_Shelters')
BEGIN
    ALTER TABLE News
    ADD CONSTRAINT FK_News_Shelters
    FOREIGN KEY (ShelterID) REFERENCES Shelters(ShelterID);
    PRINT 'Внешний ключ FK_News_Shelters добавлен';
END
ELSE
BEGIN
    PRINT 'Внешний ключ FK_News_Shelters уже существует';
END
GO

-- 6. Создаем несколько тестовых приютов (если их еще нет)
IF NOT EXISTS (SELECT 1 FROM Shelters)
BEGIN
    INSERT INTO Shelters (ShelterName, Address, Phone, Email, Description)
    VALUES 
        (N'Приют "Надежда"', N'г. Москва, ул. Ленина, д. 10', '+7 (495) 123-45-67', 'nadezhda@shelter.ru', N'Главный приют в центре города'),
        (N'Приют "Дружба"', N'г. Москва, ул. Мира, д. 25', '+7 (495) 234-56-78', 'druzhba@shelter.ru', N'Филиал на севере города'),
        (N'Приют "Верность"', N'г. Москва, ул. Победы, д. 5', '+7 (495) 345-67-89', 'vernost@shelter.ru', N'Филиал на юге города');
    PRINT 'Тестовые приюты добавлены';
END
ELSE
BEGIN
    PRINT 'Приюты уже существуют';
END
GO

PRINT 'Миграция приютов завершена!';
GO



