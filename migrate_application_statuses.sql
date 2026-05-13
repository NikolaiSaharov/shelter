-- Миграция статусов заявок: замена IsApproved на таблицу ApplicationStatuses
-- Создание таблицы статусов заявок

USE AnimalShelterDB;
GO

-- 1. Создаем таблицу статусов заявок
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'ApplicationStatuses')
BEGIN
    CREATE TABLE ApplicationStatuses (
        StatusID INT PRIMARY KEY IDENTITY(1,1),
        StatusName NVARCHAR(20) NOT NULL UNIQUE CHECK (StatusName IN ('Pending', 'Approved', 'Rejected'))
    );
    PRINT 'Таблица ApplicationStatuses создана';
END
ELSE
BEGIN
    PRINT 'Таблица ApplicationStatuses уже существует';
END
GO

-- 2. Заполняем статусы
IF NOT EXISTS (SELECT 1 FROM ApplicationStatuses WHERE StatusName = 'Pending')
BEGIN
    INSERT INTO ApplicationStatuses (StatusName) VALUES ('Pending');
    PRINT 'Статус "Pending" добавлен';
END
GO

IF NOT EXISTS (SELECT 1 FROM ApplicationStatuses WHERE StatusName = 'Approved')
BEGIN
    INSERT INTO ApplicationStatuses (StatusName) VALUES ('Approved');
    PRINT 'Статус "Approved" добавлен';
END
GO

IF NOT EXISTS (SELECT 1 FROM ApplicationStatuses WHERE StatusName = 'Rejected')
BEGIN
    INSERT INTO ApplicationStatuses (StatusName) VALUES ('Rejected');
    PRINT 'Статус "Rejected" добавлен';
END
GO

-- 3. Добавляем новое поле StatusID в таблицу Applications
IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('Applications') AND name = 'StatusID')
BEGIN
    ALTER TABLE Applications ADD StatusID INT NULL;
    PRINT 'Поле StatusID добавлено в таблицу Applications';
END
ELSE
BEGIN
    PRINT 'Поле StatusID уже существует в таблице Applications';
END
GO

-- 4. Мигрируем данные: конвертируем IsApproved в StatusID
-- Получаем ID статусов
DECLARE @PendingStatusID INT = (SELECT StatusID FROM ApplicationStatuses WHERE StatusName = 'Pending');
DECLARE @ApprovedStatusID INT = (SELECT StatusID FROM ApplicationStatuses WHERE StatusName = 'Approved');
DECLARE @RejectedStatusID INT = (SELECT StatusID FROM ApplicationStatuses WHERE StatusName = 'Rejected');

-- Обновляем StatusID на основе IsApproved и наличия маркера ОТКЛОНЕНО_ в Comment
UPDATE Applications
SET StatusID = CASE
    WHEN IsApproved = 1 THEN @ApprovedStatusID
    WHEN Comment IS NOT NULL AND Comment LIKE '%ОТКЛОНЕНО_%' THEN @RejectedStatusID
    ELSE @PendingStatusID
END
WHERE StatusID IS NULL;

PRINT 'Данные мигрированы из IsApproved в StatusID';
GO

-- 5. Устанавливаем значение по умолчанию для новых записей
-- Получаем StatusID для Pending и устанавливаем его как значение по умолчанию через динамический SQL
DECLARE @PendingStatusID INT;
DECLARE @SQL NVARCHAR(MAX);

SELECT @PendingStatusID = StatusID FROM ApplicationStatuses WHERE StatusName = 'Pending';

IF @PendingStatusID IS NOT NULL
BEGIN
    -- Проверяем, существует ли уже constraint
    IF NOT EXISTS (SELECT * FROM sys.default_constraints WHERE name = 'DF_Applications_StatusID')
    BEGIN
        SET @SQL = N'ALTER TABLE Applications ADD CONSTRAINT DF_Applications_StatusID DEFAULT ' + CAST(@PendingStatusID AS NVARCHAR(10)) + ' FOR StatusID';
        EXEC sp_executesql @SQL;
        PRINT 'Значение по умолчанию для StatusID установлено';
    END
    ELSE
    BEGIN
        PRINT 'Constraint DF_Applications_StatusID уже существует';
    END
END
ELSE
BEGIN
    PRINT 'ОШИБКА: Статус Pending не найден';
END
GO

-- 6. Делаем StatusID NOT NULL
ALTER TABLE Applications
ALTER COLUMN StatusID INT NOT NULL;
GO

-- 7. Добавляем внешний ключ
IF NOT EXISTS (SELECT * FROM sys.foreign_keys WHERE name = 'FK_Applications_ApplicationStatuses')
BEGIN
    ALTER TABLE Applications
    ADD CONSTRAINT FK_Applications_ApplicationStatuses
    FOREIGN KEY (StatusID) REFERENCES ApplicationStatuses(StatusID);
    PRINT 'Внешний ключ FK_Applications_ApplicationStatuses добавлен';
END
GO

-- 8. Удаляем старое поле IsApproved (после проверки, что все данные мигрированы)
-- ВНИМАНИЕ: Раскомментируйте следующую строку только после проверки данных!
-- ALTER TABLE Applications DROP COLUMN IsApproved;
-- PRINT 'Поле IsApproved удалено';

-- 9. Обновляем представление vw_ApplicationReport
IF EXISTS (SELECT * FROM sys.views WHERE name = 'vw_ApplicationReport')
BEGIN
    DROP VIEW vw_ApplicationReport;
END
GO

CREATE VIEW vw_ApplicationReport AS
SELECT 
    app.ApplicationID, 
    ast.StatusName AS Status,
    app.ApplicationDate,
    u.FirstName + ' ' + u.LastName AS UserName, 
    r.RoleName, 
    a.AnimalName AS AnimalName
FROM Applications app
INNER JOIN ApplicationStatuses ast ON app.StatusID = ast.StatusID
INNER JOIN Users u ON app.UserID = u.UserID
INNER JOIN Roles r ON u.RoleID = r.RoleID
INNER JOIN Animals a ON app.AnimalID = a.AnimalID;
GO

PRINT 'Представление vw_ApplicationReport обновлено';
GO

-- 10. Обновляем хранимую процедуру sp_GetAdoptionStats
IF EXISTS (SELECT * FROM sys.procedures WHERE name = 'sp_GetAdoptionStats')
BEGIN
    DROP PROCEDURE sp_GetAdoptionStats;
END
GO

CREATE PROCEDURE sp_GetAdoptionStats
    @StartDate DATE,
    @EndDate DATE
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        DECLARE @AdoptedStatusID INT;
        DECLARE @ApprovedStatusID INT;
        SELECT @AdoptedStatusID = StatusID FROM AnimalStatuses WHERE StatusName = 'Adopted';
        SELECT @ApprovedStatusID = StatusID FROM ApplicationStatuses WHERE StatusName = 'Approved';
        
        SELECT 
            COUNT(*) AS TotalAdoptions,
            SUM(CASE WHEN a.StatusID = @AdoptedStatusID THEN 1 ELSE 0 END) AS AdoptedCount,
            AVG(CAST(a.Age AS FLOAT)) AS AverageAge
        FROM Applications app
        INNER JOIN Animals a ON app.AnimalID = a.AnimalID
        WHERE app.ApplicationDate BETWEEN @StartDate AND @EndDate
        AND app.StatusID = @ApprovedStatusID;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK;
        DECLARE @ErrorMessage NVARCHAR(4000) = ERROR_MESSAGE();
        DECLARE @ErrorSeverity INT = ERROR_SEVERITY();
        DECLARE @ErrorState INT = ERROR_STATE();
        RAISERROR (@ErrorMessage, @ErrorSeverity, @ErrorState);
    END CATCH
END;
GO

PRINT 'Процедура sp_GetAdoptionStats обновлена';
GO

-- Проверка миграции
SELECT 
    ast.StatusName,
    COUNT(*) AS ApplicationCount
FROM Applications app
INNER JOIN ApplicationStatuses ast ON app.StatusID = ast.StatusID
GROUP BY ast.StatusName
ORDER BY ast.StatusName;

PRINT 'Миграция завершена!';
GO

