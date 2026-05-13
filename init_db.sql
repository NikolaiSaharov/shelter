CREATE DATABASE AnimalShelterDB;

GO

USE AnimalShelterDB;

GO

CREATE TABLE AnimalStatuses (
    StatusID INT PRIMARY KEY IDENTITY(1,1),
    StatusName NVARCHAR(20) NOT NULL UNIQUE CHECK (StatusName IN ('Available', 'Adopted', 'Pending'))
);

GO

CREATE TABLE Roles (
    RoleID INT PRIMARY KEY IDENTITY(1,1),
    RoleName NVARCHAR(20) NOT NULL UNIQUE CHECK (RoleName IN ('Guest', 'Manager', 'Admin'))
);

GO

CREATE TABLE AnimalTypes (
    TypeID INT PRIMARY KEY IDENTITY(1,1),
    TypeName NVARCHAR(50) NOT NULL UNIQUE CHECK (TypeName <> '')
);

GO

CREATE TABLE Breeds (
    BreedID INT PRIMARY KEY IDENTITY(1,1),
    BreedName NVARCHAR(100) NOT NULL UNIQUE CHECK (BreedName <> ''),
    TypeID INT NOT NULL,
    FOREIGN KEY (TypeID) REFERENCES AnimalTypes(TypeID) ON DELETE CASCADE
);

GO

CREATE TABLE Animals (
    AnimalID INT PRIMARY KEY IDENTITY(1,1),
    AnimalName NVARCHAR(50) NOT NULL CHECK (AnimalName <> ''),  
    Age INT NOT NULL CHECK (Age >= 0),
    Gender NVARCHAR(10) NOT NULL CHECK (Gender IN ('Male', 'Female', 'Unknown')),
    Vaccinated BIT NOT NULL DEFAULT 0,
    Description NVARCHAR(MAX),
    ImagePath NVARCHAR(255) NULL,  
    StatusID INT NOT NULL DEFAULT 1,  
    BreedID INT NOT NULL,
    FOREIGN KEY (BreedID) REFERENCES Breeds(BreedID) ON DELETE CASCADE,
    FOREIGN KEY (StatusID) REFERENCES AnimalStatuses(StatusID)
);

GO

CREATE TABLE AnimalCharacters (
    CharacterID INT PRIMARY KEY IDENTITY(1,1),
    CharacterName NVARCHAR(50) NOT NULL UNIQUE CHECK (CharacterName <> ''),
    Description NVARCHAR(255) NULL
);

GO

ALTER TABLE Animals ADD 
    CharacterID INT NULL,
    Height DECIMAL(5,2) NULL CHECK (Height > 0),
    AnimalWeight DECIMAL(5,2) NULL CHECK (AnimalWeight > 0),  
    FOREIGN KEY (CharacterID) REFERENCES AnimalCharacters(CharacterID);

GO

CREATE TABLE VaccinationTypes (
    VaccinationTypeID INT PRIMARY KEY IDENTITY(1,1),
    VaccinationName NVARCHAR(100) NOT NULL UNIQUE CHECK (VaccinationName <> ''),
    Description NVARCHAR(255)
);

GO

CREATE TABLE AnimalVaccinations (
    AnimalVaccinationID INT PRIMARY KEY IDENTITY(1,1),  
    AnimalID INT NOT NULL,
    VaccinationTypeID INT NOT NULL,
    FOREIGN KEY (AnimalID) REFERENCES Animals(AnimalID) ON DELETE CASCADE,
    FOREIGN KEY (VaccinationTypeID) REFERENCES VaccinationTypes(VaccinationTypeID) ON DELETE CASCADE
);

GO

CREATE TABLE VaccinationRecords (
    RecordID INT PRIMARY KEY IDENTITY(1,1),
    AnimalVaccinationID INT NOT NULL,
    VaccinationDate DATE NOT NULL DEFAULT GETDATE(),
    FOREIGN KEY (AnimalVaccinationID) REFERENCES AnimalVaccinations(AnimalVaccinationID) ON DELETE CASCADE
);

GO

CREATE TABLE Users (
    UserID INT PRIMARY KEY IDENTITY(1,1),
    Email NVARCHAR(100) NOT NULL UNIQUE CHECK (Email LIKE '%@%'),
    PasswordHash NVARCHAR(255) NOT NULL CHECK (PasswordHash <> ''),
    LastName NVARCHAR(50) NOT NULL CHECK (LastName <> ''),       
    FirstName NVARCHAR(50) NOT NULL CHECK (FirstName <> ''),     
    MiddleName NVARCHAR(50) NULL,                                
    Phone NVARCHAR(20) NOT NULL CHECK (Phone LIKE '+[0-9]%'),    
    RegistrationDate DATETIME NOT NULL DEFAULT GETDATE(),
    RoleID INT NOT NULL,
    FOREIGN KEY (RoleID) REFERENCES Roles(RoleID) ON DELETE NO ACTION
);

GO

-- Приюты (нужно для привязки животных и менеджеров)
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
GO

-- Привязка пользователя (менеджера) к приюту
ALTER TABLE Users ADD ShelterID INT NULL;
GO
ALTER TABLE Users
ADD CONSTRAINT FK_Users_Shelters
FOREIGN KEY (ShelterID) REFERENCES Shelters(ShelterID);
GO

CREATE TABLE Applications (
    ApplicationID INT PRIMARY KEY IDENTITY(1,1),
    UserID INT NOT NULL,
    AnimalID INT NOT NULL,
    ApplicationDate DATETIME NOT NULL DEFAULT GETDATE(),
    IsApproved BIT NOT NULL DEFAULT 0,  
    Reason NVARCHAR(500) NOT NULL CHECK (Reason <> ''),          
    Experience NVARCHAR(500) NULL,                               
    HousingConditions NVARCHAR(500) NULL,                        
    Comment NVARCHAR(MAX) NULL,                                  
    FOREIGN KEY (UserID) REFERENCES Users(UserID) ON DELETE CASCADE,
    FOREIGN KEY (AnimalID) REFERENCES Animals(AnimalID) ON DELETE CASCADE
);

GO

CREATE TABLE Messages (
    MessageID INT PRIMARY KEY IDENTITY(1,1),
    SenderID INT NOT NULL,
    ParentMessageID INT NULL, 
    SubjectMessages NVARCHAR(200) NULL, 
    MessageText NVARCHAR(MAX) NOT NULL CHECK (MessageText <> ''),
    SendDate DATETIME NOT NULL DEFAULT GETDATE(),
    IsRead BIT NOT NULL DEFAULT 0,
    RecipientRole NVARCHAR(20) NULL CHECK (RecipientRole IN ('Manager', 'Admin') OR RecipientRole IS NULL),
    FOREIGN KEY (SenderID) REFERENCES Users(UserID),
    FOREIGN KEY (ParentMessageID) REFERENCES Messages(MessageID) 
);

GO

CREATE TABLE Donations (
    DonationID INT PRIMARY KEY IDENTITY(1,1),
    UserID INT NOT NULL,
    AnimalID INT NOT NULL,
    Amount DECIMAL(10, 2) NOT NULL CHECK (Amount > 0),
    DonationDate DATETIME NOT NULL DEFAULT GETDATE(),
    Comment NVARCHAR(255),
    IsApproved BIT NOT NULL DEFAULT 0,  
    FOREIGN KEY (UserID) REFERENCES Users(UserID) ON DELETE CASCADE,
    FOREIGN KEY (AnimalID) REFERENCES Animals(AnimalID) ON DELETE CASCADE
);

GO

CREATE TABLE News (
    NewsID INT PRIMARY KEY IDENTITY(1,1),
    UserID INT NOT NULL,
    Title NVARCHAR(100) NOT NULL CHECK (Title <> ''),
    Content NVARCHAR(MAX) NOT NULL CHECK (Content <> ''),
    PostDate DATETIME NOT NULL DEFAULT GETDATE(),
    IsPublished BIT NOT NULL DEFAULT 1,
    ImagePath NVARCHAR(255) NULL,
    FOREIGN KEY (UserID) REFERENCES Users(UserID) ON DELETE CASCADE
);

GO

CREATE TABLE UserProfiles (
    ProfileID INT PRIMARY KEY IDENTITY(1,1),
    UserID INT NOT NULL UNIQUE,
    HomeAddress NVARCHAR(255) NULL,
    DateOfBirth DATE NULL CHECK (DateOfBirth <= GETDATE()),
    ProfilePicture NVARCHAR(255) NULL,
    CreatedDate DATETIME NOT NULL DEFAULT GETDATE(),
    UpdatedDate DATETIME NOT NULL DEFAULT GETDATE(),
    FOREIGN KEY (UserID) REFERENCES Users(UserID) ON DELETE CASCADE
);

GO

CREATE TABLE MeetingStatuses (
    MeetingStatusID INT PRIMARY KEY IDENTITY(1,1),
    StatusName NVARCHAR(20) NOT NULL UNIQUE CHECK (StatusName IN ('Scheduled', 'InProgress', 'Completed', 'Cancelled', 'NoShow'))
);

GO

CREATE TABLE VideoMeetings (
    MeetingID INT PRIMARY KEY IDENTITY(1,1),
    ApplicationID INT NOT NULL,
    MeetingStatusID INT NOT NULL DEFAULT 1,
    MeetingTitle NVARCHAR(200) NOT NULL CHECK (MeetingTitle <> ''),
    MeetingDescription NVARCHAR(500) NULL,
    MeetingLink NVARCHAR(500) NOT NULL CHECK (MeetingLink <> ''),
    ScheduledDateTime DATETIME2 NOT NULL,
    MeetingDuration INT NOT NULL CHECK (MeetingDuration > 0),
    CreatedByUserID INT NOT NULL,
    CreatedDateTime DATETIME2 NOT NULL DEFAULT GETDATE(),
    LastModifiedDateTime DATETIME2 NOT NULL DEFAULT GETDATE(),
    FOREIGN KEY (ApplicationID) REFERENCES Applications(ApplicationID) ON DELETE CASCADE,
    FOREIGN KEY (MeetingStatusID) REFERENCES MeetingStatuses(MeetingStatusID),
    FOREIGN KEY (CreatedByUserID) REFERENCES Users(UserID)
);

GO

CREATE TABLE MeetingParticipants (
    ParticipantID INT PRIMARY KEY IDENTITY(1,1),
    MeetingID INT NOT NULL,
    UserID INT NOT NULL,
    ParticipantRole NVARCHAR(20) NOT NULL CHECK (ParticipantRole IN ('Host', 'Attendee')),
    FOREIGN KEY (MeetingID) REFERENCES VideoMeetings(MeetingID) ON DELETE CASCADE,
    FOREIGN KEY (UserID) REFERENCES Users(UserID),
    UNIQUE (MeetingID, UserID)
);

GO

CREATE TABLE AnimalMedicalRecords (
    RecordID INT PRIMARY KEY IDENTITY(1,1),
    AnimalID INT NOT NULL,
    ConditionName NVARCHAR(100) NOT NULL,
    DiagnosisDate DATE NULL,
    Treatment NVARCHAR(500) NULL,
    Status NVARCHAR(20) DEFAULT 'Active' CHECK (Status IN ('Active', 'Resolved', 'Chronic')),
    Notes NVARCHAR(MAX) NULL,
    FOREIGN KEY (AnimalID) REFERENCES Animals(AnimalID) ON DELETE CASCADE
);

GO

CREATE TABLE ActivityTypes (
    ActivityTypeID INT PRIMARY KEY IDENTITY(1,1),
    ActivityName NVARCHAR(50) NOT NULL UNIQUE,
    Description NVARCHAR(255) NULL
);

GO

CREATE TABLE FrequencyTypes (
    FrequencyID INT PRIMARY KEY IDENTITY(1,1),
    FrequencyName NVARCHAR(50) NOT NULL UNIQUE,
    Description NVARCHAR(255) NULL
);

GO

CREATE TABLE AnimalCareSchedule (
    ScheduleID INT PRIMARY KEY IDENTITY(1,1),
    AnimalID INT NOT NULL,
    ActivityTypeID INT NOT NULL,
    FrequencyID INT NOT NULL,
    ScheduleTime TIME NULL,
    Notes NVARCHAR(255) NULL,
    IsActive BIT DEFAULT 1,
    FOREIGN KEY (AnimalID) REFERENCES Animals(AnimalID) ON DELETE CASCADE,
    FOREIGN KEY (ActivityTypeID) REFERENCES ActivityTypes(ActivityTypeID),
    FOREIGN KEY (FrequencyID) REFERENCES FrequencyTypes(FrequencyID)
);

GO

ALTER TABLE Animals ADD AdmissionDate DATE NULL;

GO

INSERT INTO ActivityTypes (ActivityName, Description) VALUES 
('Feeding', 'Кормление животного'),
('Medication', 'Прием лекарств'),
('Grooming', 'Уход за шерстью/гигиена'),
('Exercise', 'Прогулка/физическая активность'),
('Training', 'Дрессировка/обучение'),
('Veterinary Check', 'Осмотр ветеринара'),
('Socialization', 'Социализация с другими животными'),
('Cleaning', 'Уборка места обитания');

GO

INSERT INTO FrequencyTypes (FrequencyName, Description) VALUES 
('Daily', 'Ежедневно'),
('Twice Daily', 'Дважды в день'),
('Weekly', 'Еженедельно'),
('Bi-Weekly', 'Дважды в неделю'),
('Monthly', 'Ежемесячно'),
('As Needed', 'По необходимости'),
('Every 2 Days', 'Каждые 2 дня'),
('Every 3 Days', 'Каждые 3 дня');

GO

INSERT INTO MeetingStatuses (StatusName) VALUES 
('Scheduled'),
('InProgress'),
('Completed'),
('Cancelled'),
('NoShow');

GO

CREATE TRIGGER trg_UpdateMeetingModifiedDate
ON VideoMeetings
AFTER UPDATE
AS
BEGIN
    UPDATE VideoMeetings 
    SET LastModifiedDateTime = GETDATE()
    WHERE MeetingID IN (SELECT MeetingID FROM inserted)
END;

GO

CREATE TRIGGER trg_NotifyMeetingScheduled
ON VideoMeetings
AFTER INSERT
AS
BEGIN
    DECLARE @ManagerID INT;
    SELECT @ManagerID = UserID FROM Users WHERE RoleID = (SELECT RoleID FROM Roles WHERE RoleName = 'Manager');
    IF @ManagerID IS NOT NULL
    BEGIN
        INSERT INTO ManagerNotifications (UserID, Message)
        SELECT 
            @ManagerID,
            'Запланирована видеовстреча для заявки №' + CAST(i.ApplicationID AS NVARCHAR(10)) + 
            ' на ' + CONVERT(NVARCHAR(20), i.ScheduledDateTime, 120)
        FROM inserted i;
    END
END;

GO

CREATE VIEW vw_MeetingDetails AS
SELECT 
    vm.MeetingID,
    vm.MeetingTitle,
    vm.MeetingDescription,
    vm.MeetingLink,
    vm.ScheduledDateTime,
    vm.MeetingDuration,
    ms.StatusName AS MeetingStatus,
    a.ApplicationID,
    u_app.FirstName + ' ' + u_app.LastName AS ApplicantName,
    anim.AnimalName,
    u_creator.FirstName + ' ' + u_creator.LastName AS CreatedByName,
    vm.CreatedDateTime
FROM VideoMeetings vm
INNER JOIN MeetingStatuses ms ON vm.MeetingStatusID = ms.MeetingStatusID
INNER JOIN Applications a ON vm.ApplicationID = a.ApplicationID
INNER JOIN Users u_app ON a.UserID = u_app.UserID
INNER JOIN Animals anim ON a.AnimalID = anim.AnimalID
INNER JOIN Users u_creator ON vm.CreatedByUserID = u_creator.UserID;

GO

CREATE VIEW vw_MeetingParticipants AS
SELECT 
    mp.ParticipantID,
    mp.MeetingID,
    vm.MeetingTitle,
    u.UserID,
    u.FirstName + ' ' + u.LastName AS ParticipantName,
    u.Email,
    mp.ParticipantRole
FROM MeetingParticipants mp
INNER JOIN VideoMeetings vm ON mp.MeetingID = vm.MeetingID
INNER JOIN Users u ON mp.UserID = u.UserID;

GO

CREATE TRIGGER trg_UpdateUserProfileDate
ON UserProfiles
AFTER UPDATE
AS
BEGIN
    UPDATE UserProfiles 
    SET UpdatedDate = GETDATE()
    WHERE ProfileID IN (SELECT ProfileID FROM inserted)
END;

GO

CREATE OR ALTER VIEW vw_AnimalCatalog AS
SELECT 
    a.AnimalID, 
    a.AnimalName, 
    a.Age, 
    a.Gender, 
    a.Vaccinated, 
    a.Height,
    a.AnimalWeight,  
    s.StatusName AS Status,
    b.BreedName, 
    t.TypeName,
    ac.CharacterName,
    a.ImagePath
FROM Animals a
INNER JOIN Breeds b ON a.BreedID = b.BreedID
INNER JOIN AnimalTypes t ON b.TypeID = t.TypeID
INNER JOIN AnimalStatuses s ON a.StatusID = s.StatusID
LEFT JOIN AnimalCharacters ac ON a.CharacterID = ac.CharacterID
WHERE s.StatusName = 'Available';

GO

CREATE VIEW vw_ApplicationReport AS
SELECT 
    app.ApplicationID, 
    CASE WHEN app.IsApproved = 1 THEN 'Approved' ELSE 'Pending' END AS Status,
    app.ApplicationDate,
    u.FirstName + ' ' + u.LastName AS UserName, 
    r.RoleName, 
    a.AnimalName AS AnimalName
FROM Applications app
INNER JOIN Users u ON app.UserID = u.UserID
INNER JOIN Roles r ON u.RoleID = r.RoleID
INNER JOIN Animals a ON app.AnimalID = a.AnimalID;

GO

CREATE VIEW vw_AnimalVaccinations AS
SELECT 
    a.AnimalID, 
    a.AnimalName,
    vt.VaccinationName, 
    vr.VaccinationDate
FROM Animals a
INNER JOIN AnimalVaccinations av ON a.AnimalID = av.AnimalID
INNER JOIN VaccinationTypes vt ON av.VaccinationTypeID = vt.VaccinationTypeID
LEFT JOIN VaccinationRecords vr ON av.AnimalVaccinationID = vr.AnimalVaccinationID;

GO

CREATE VIEW vw_BreedStats AS
SELECT 
    b.BreedName, 
    COUNT(a.AnimalID) AS AnimalCount
FROM Animals a
JOIN Breeds b ON a.BreedID = b.BreedID
GROUP BY b.BreedName;

GO

CREATE TRIGGER trg_CheckAnimalAge
ON Animals
AFTER INSERT, UPDATE
AS
BEGIN
    IF EXISTS (SELECT 1 FROM inserted WHERE Age < 0)
    BEGIN
        RAISERROR('Age cannot be negative', 16, 1);
        ROLLBACK TRANSACTION;
    END
END;

GO

CREATE OR ALTER PROCEDURE sp_ManageAnimal
    @Action NVARCHAR(10),
    @AnimalID INT = NULL,
    @AnimalName NVARCHAR(50) = NULL,  
    @Age INT = NULL,
    @Gender NVARCHAR(10) = NULL,
    @Vaccinated BIT = NULL,
    @Description NVARCHAR(MAX) = NULL,
    @ImagePath NVARCHAR(255) = NULL,
    @StatusID INT = NULL,  
    @BreedID INT = NULL,
    @CharacterID INT = NULL,
    @Height DECIMAL(5,2) = NULL,
    @AnimalWeight DECIMAL(5,2) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        BEGIN TRANSACTION;
        
        IF @Action = 'INSERT'
        BEGIN
            IF @AnimalName IS NULL OR @Age IS NULL OR @Gender IS NULL OR @BreedID IS NULL
                THROW 50001, 'Missing required fields for insert.', 1;
            INSERT INTO Animals (AnimalName, Age, Gender, Vaccinated, Description, ImagePath, StatusID, BreedID, CharacterID, Height, AnimalWeight)
            VALUES (@AnimalName, @Age, @Gender, @Vaccinated, @Description, @ImagePath, ISNULL(@StatusID, 1), @BreedID, @CharacterID, @Height, @AnimalWeight);
            COMMIT;
            RETURN SCOPE_IDENTITY();
        END
        ELSE IF @Action = 'UPDATE'
        BEGIN
            IF @AnimalID IS NULL
                THROW 50002, 'AnimalID required for update.', 1;
            UPDATE Animals SET
                AnimalName = ISNULL(@AnimalName, AnimalName),
                Age = ISNULL(@Age, Age),
                Gender = ISNULL(@Gender, Gender),
                Vaccinated = ISNULL(@Vaccinated, Vaccinated),
                Description = ISNULL(@Description, Description),
                ImagePath = ISNULL(@ImagePath, ImagePath),
                StatusID = ISNULL(@StatusID, StatusID),
                BreedID = ISNULL(@BreedID, BreedID),
                CharacterID = ISNULL(@CharacterID, CharacterID),
                Height = ISNULL(@Height, Height),
                AnimalWeight = ISNULL(@AnimalWeight, AnimalWeight)
            WHERE AnimalID = @AnimalID;
            IF @@ROWCOUNT = 0
                THROW 50003, 'Animal not found.', 1;
            COMMIT;
            RETURN @AnimalID;
        END
        ELSE IF @Action = 'DELETE'
        BEGIN
            IF @AnimalID IS NULL
                THROW 50004, 'AnimalID required for delete.', 1;
            DELETE FROM Animals WHERE AnimalID = @AnimalID;
            IF @@ROWCOUNT = 0
                THROW 50005, 'Animal not found.', 1;
            COMMIT;
            RETURN 0;
        END
        ELSE
            THROW 50000, 'Invalid action.', 1;
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

CREATE OR ALTER PROCEDURE sp_GetAdoptionStats
    @StartDate DATE,
    @EndDate DATE
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        DECLARE @AdoptedStatusID INT;
        SELECT @AdoptedStatusID = StatusID FROM AnimalStatuses WHERE StatusName = 'Adopted';
        SELECT 
            COUNT(*) AS TotalAdoptions,
            SUM(CASE WHEN a.StatusID = @AdoptedStatusID THEN 1 ELSE 0 END) AS AdoptedCount,
            AVG(CAST(a.Age AS FLOAT)) AS AverageAge
        FROM Applications app
        INNER JOIN Animals a ON app.AnimalID = a.AnimalID
        WHERE app.ApplicationDate BETWEEN @StartDate AND @EndDate
        AND app.IsApproved = 1;
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

CREATE TABLE AuditLogs (
    AuditID INT PRIMARY KEY IDENTITY(1,1),
    TableName NVARCHAR(50) NOT NULL,
    RecordID INT NOT NULL,
    Action NVARCHAR(20) NOT NULL, 
    ChangedBy INT NOT NULL, 
    ChangeDate DATETIME NOT NULL DEFAULT GETDATE(),
    OldValue NVARCHAR(MAX),
    NewValue NVARCHAR(MAX),
    FOREIGN KEY (ChangedBy) REFERENCES Users(UserID)
);

GO

CREATE TRIGGER trg_AuditAnimals
ON Animals
AFTER INSERT, UPDATE, DELETE
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @UserID INT = (SELECT MIN(UserID) FROM Users);
    DECLARE @OldValue NVARCHAR(MAX), @NewValue NVARCHAR(MAX);
    IF @UserID IS NULL
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM Roles WHERE RoleName='Admin')
            INSERT INTO Roles (RoleName) VALUES ('Admin');
        INSERT INTO Users (Email, PasswordHash, LastName, FirstName, MiddleName, Phone, RoleID)
        VALUES ('system@local', 'system', N'System', N'User', NULL, '+70000000000',
                (SELECT RoleID FROM Roles WHERE RoleName='Admin'));
        SET @UserID = SCOPE_IDENTITY();
    END
    IF EXISTS (SELECT 1 FROM inserted)
        SELECT @NewValue = (SELECT * FROM inserted FOR JSON PATH, WITHOUT_ARRAY_WRAPPER);
    IF EXISTS (SELECT 1 FROM deleted)
        SELECT @OldValue = (SELECT * FROM deleted FOR JSON PATH, WITHOUT_ARRAY_WRAPPER);
    INSERT INTO AuditLogs (TableName, RecordID, Action, ChangedBy, OldValue, NewValue)
    VALUES (
        'Animals',
        COALESCE((SELECT TOP 1 AnimalID FROM inserted), (SELECT TOP 1 AnimalID FROM deleted)),
        CASE 
            WHEN EXISTS (SELECT 1 FROM inserted) AND EXISTS (SELECT 1 FROM deleted) THEN 'UPDATE'
            WHEN EXISTS (SELECT 1 FROM inserted) THEN 'INSERT'
            ELSE 'DELETE'
        END,
        @UserID,
        @OldValue,
        @NewValue
    );
END;

GO

CREATE OR ALTER VIEW vw_LatestNews AS
SELECT TOP 5 
    n.NewsID, 
    n.Title, 
    n.Content, 
    n.PostDate, 
    u.FirstName + ' ' + u.LastName AS AuthorName,  
    r.RoleName
FROM News n
INNER JOIN Users u ON n.UserID = u.UserID
INNER JOIN Roles r ON u.RoleID = r.RoleID
WHERE n.IsPublished = 1
ORDER BY n.PostDate DESC;

GO

CREATE TABLE ManagerNotifications (
    NotificationID INT PRIMARY KEY IDENTITY(1,1),
    UserID INT NOT NULL, 
    Message NVARCHAR(255) NOT NULL,
    CreatedDate DATETIME NOT NULL DEFAULT GETDATE(),
    IsRead BIT NOT NULL DEFAULT 0,
    FOREIGN KEY (UserID) REFERENCES Users(UserID)
);

GO

CREATE TRIGGER trg_NotifyManagerOnDonation
ON Donations
AFTER INSERT
AS
BEGIN
    DECLARE @ManagerID INT;
    SELECT @ManagerID = UserID FROM Users WHERE RoleID = (SELECT RoleID FROM Roles WHERE RoleName = 'Manager');
    IF @ManagerID IS NOT NULL
    BEGIN
        INSERT INTO ManagerNotifications (UserID, Message)
        VALUES (@ManagerID, 'New donation received for AnimalID ' + CAST((SELECT AnimalID FROM inserted) AS NVARCHAR(10)) + ' with amount ' + CAST((SELECT Amount FROM inserted) AS NVARCHAR(10)));
    END
END;

GO

CREATE TRIGGER trg_NotifyManagerOnApplication
ON Applications
AFTER INSERT
AS
BEGIN
    DECLARE @ManagerID INT;
    SELECT @ManagerID = UserID FROM Users WHERE RoleID = (SELECT RoleID FROM Roles WHERE RoleName = 'Manager');
    IF @ManagerID IS NOT NULL
    BEGIN
        INSERT INTO ManagerNotifications (UserID, Message)
        VALUES (@ManagerID, 'Получена новая заявка на усыновление для AnimalID ' + CAST((SELECT AnimalID FROM inserted) AS NVARCHAR(10)));
    END
END;

GO

IF NOT EXISTS (SELECT 1 FROM AnimalStatuses WHERE StatusName = 'Adopted')
BEGIN
    INSERT INTO AnimalStatuses (StatusName) VALUES ('Adopted');
END

GO

IF NOT EXISTS (SELECT 1 FROM AnimalStatuses WHERE StatusName = 'Available')
BEGIN
    INSERT INTO AnimalStatuses (StatusName) VALUES ('Available');
END

IF NOT EXISTS (SELECT 1 FROM AnimalStatuses WHERE StatusName = 'Pending')
BEGIN
    INSERT INTO AnimalStatuses (StatusName) VALUES ('Pending');
END

GO

IF NOT EXISTS (SELECT 1 FROM AnimalTypes WHERE TypeName='Dog')
    INSERT INTO AnimalTypes (TypeName) VALUES ('Dog');

IF NOT EXISTS (SELECT 1 FROM AnimalTypes WHERE TypeName='Cat')
    INSERT INTO AnimalTypes (TypeName) VALUES ('Cat');

GO

INSERT INTO Breeds (BreedName, TypeID)
SELECT 'Labrador', (SELECT TypeID FROM AnimalTypes WHERE TypeName='Dog')
WHERE NOT EXISTS (SELECT 1 FROM Breeds WHERE BreedName='Labrador');

INSERT INTO Breeds (BreedName, TypeID)
SELECT 'Terrier', (SELECT TypeID FROM AnimalTypes WHERE TypeName='Dog')
WHERE NOT EXISTS (SELECT 1 FROM Breeds WHERE BreedName='Terrier');

INSERT INTO Breeds (BreedName, TypeID)
SELECT 'British Shorthair', (SELECT TypeID FROM AnimalTypes WHERE TypeName='Cat')
WHERE NOT EXISTS (SELECT 1 FROM Breeds WHERE BreedName='British Shorthair');

GO

INSERT INTO AnimalCharacters (CharacterName, Description)
SELECT 'Calm', N'Спокойный, дружелюбный'
WHERE NOT EXISTS (SELECT 1 FROM AnimalCharacters WHERE CharacterName='Calm');

INSERT INTO AnimalCharacters (CharacterName, Description)
SELECT 'Active', N'Активный, игривый'
WHERE NOT EXISTS (SELECT 1 FROM AnimalCharacters WHERE CharacterName='Active');

GO

INSERT INTO Animals
(AnimalName, Age, Gender, Vaccinated, Description, ImagePath, StatusID, BreedID, CharacterID, Height, AnimalWeight, AdmissionDate)
SELECT
N'Гаф', 1, 'Male', 1,
N'Дружелюбный и энергичный пёс.',
'https://images.unsplash.com/photo-1548199973-03cce0bbc87b?w=1200&q=80',
(SELECT StatusID FROM AnimalStatuses WHERE StatusName='Available'),
(SELECT BreedID FROM Breeds WHERE BreedName='Labrador'),
(SELECT CharacterID FROM AnimalCharacters WHERE CharacterName='Active'),
45.0, 12.0, GETDATE()
WHERE NOT EXISTS (SELECT 1 FROM Animals WHERE AnimalName=N'Гаф');

INSERT INTO Animals
(AnimalName, Age, Gender, Vaccinated, Description, ImagePath, StatusID, BreedID, CharacterID, Height, AnimalWeight, AdmissionDate)
SELECT
N'Чеси', 1, 'Female', 1,
N'Умная и ласковая.',
'https://images.unsplash.com/photo-1507146426996-ef05306b995a?w=1200&q=80',
(SELECT StatusID FROM AnimalStatuses WHERE StatusName='Available'),
(SELECT BreedID FROM Breeds WHERE BreedName='Terrier'),
(SELECT CharacterID FROM AnimalCharacters WHERE CharacterName='Calm'),
30.0, 9.0, GETDATE()
WHERE NOT EXISTS (SELECT 1 FROM Animals WHERE AnimalName=N'Чеси');

INSERT INTO Animals
(AnimalName, Age, Gender, Vaccinated, Description, ImagePath, StatusID, BreedID, CharacterID, Height, AnimalWeight, AdmissionDate)
SELECT
N'Муся', 2, 'Female', 0,
N'Спокойная и нежная кошка.',
'https://images.unsplash.com/photo-1518791841217-8f162f1e1131?w=1200&q=80',
(SELECT StatusID FROM AnimalStatuses WHERE StatusName='Available'),
(SELECT BreedID FROM Breeds WHERE BreedName='British Shorthair'),
(SELECT CharacterID FROM AnimalCharacters WHERE CharacterName='Calm'),
22.0, 4.2, GETDATE()
WHERE NOT EXISTS (SELECT 1 FROM Animals WHERE AnimalName=N'Муся');

INSERT INTO Animals
(AnimalName, Age, Gender, Vaccinated, Description, ImagePath, StatusID, BreedID, CharacterID, Height, AnimalWeight, AdmissionDate)
SELECT
N'Лева', 0, 'Male', 0,
N'Любопытный котёнок, быстро привыкает к людям.',
'https://images.unsplash.com/photo-1518020382113-a7e8fc38eac9?w=1200&q=80',
(SELECT StatusID FROM AnimalStatuses WHERE StatusName='Available'),
(SELECT BreedID FROM Breeds WHERE BreedName='British Shorthair'),
(SELECT CharacterID FROM AnimalCharacters WHERE CharacterName='Active'),
18.0, 2.0, GETDATE()
WHERE NOT EXISTS (SELECT 1 FROM Animals WHERE AnimalName=N'Лева');

GO

UPDATE Animals
SET ImagePath = 'https://i.pinimg.com/originals/6e/9b/32/6e9b32425b1c7639b4652eaa14eb57c5.jpg'
WHERE AnimalName = N'Гаф';

GO

UPDATE Animals
SET ImagePath = 'https://haski-mana.ru/wp-content/uploads/c/a/2/ca2ae3a9d857b9554a33c46128e55054.jpeg'
WHERE AnimalName = N'Чеси';

GO

UPDATE Animals
SET ImagePath = 'https://avatars.mds.yandex.net/i?id=b70de86e1bd812fee28f8720492d9f88_l-5878159-images-thumbs&n=13'
WHERE AnimalName = N'Муся';

GO

UPDATE Animals
SET ImagePath = 'https://static32.tgcnt.ru/posts/_0/47/479653d7bb3b2641d75cc3e3aaa4040e.jpg'
WHERE AnimalName = N'Лева';

GO

DECLARE @AdminUserID INT = (SELECT TOP 1 UserID FROM Users ORDER BY UserID);
INSERT INTO News (UserID, Title, Content, PostDate, IsPublished, ImagePath)
SELECT
  ISNULL(@AdminUserID, 1),
  N'Нашли дом для Гафа',
  N'<p><strong>Отличные новости!</strong> Гаф отправился в новую семью! Спасибо всем, кто помогал!</p><p>Наш любимый пёс наконец-то обрёл свой дом. <em>Это было долгое ожидание</em>, но оно того стоило.</p>',
  GETDATE(), 1,
  'https://www.google.com/url?sa=i&url=https%3A%2F%2Fwww.marieclaire.ru%2Fstil-zjizny%2Fsamyie-milyie-dikie-jivotnyie%2F&psig=AOvVaw2Ub850ahoPDFjZXEhZk9fe&ust=1761947202416000&source=images&cd=vfe&opi=89978449&ved=0CBUQjRxqFwoTCIiF0fvyzJADFQAAAAAdAAAAABAE'
WHERE NOT EXISTS (SELECT 1 FROM News WHERE Title = N'Нашли дом для Гафа');

INSERT INTO News (UserID, Title, Content, PostDate, IsPublished, ImagePath)
SELECT
  ISNULL(@AdminUserID, 1),
  N'Сбор корма на октябрь',
  N'<p>Нам нужен <strong>гипоаллергенный корм</strong> для щенков и взрослых собак.</p><p>Пожалуйста, помогите нам обеспечить наших питомцев качественным питанием.</p>',
  DATEADD(DAY, -10, GETDATE()), 1,
  'https://www.google.com/url?sa=i&url=https%3A%2F%2Fwww.kanal-o.ru%2Fnews%2F11_luchshikh_testov_o_zhivotnikh_i_prirode&psig=AOvVaw2Ub850ahoPDFjZXEhZk9fe&ust=1761947202416000&source=images&cd=vfe&opi=89978449&ved=0CBUQjRxqFwoTCIiF0fvyzJADFQAAAAAdAAAAABAL'
WHERE NOT EXISTS (SELECT 1 FROM News WHERE Title = N'Сбор корма на октябрь');

INSERT INTO News (UserID, Title, Content, PostDate, IsPublished, ImagePath)
SELECT
  ISNULL(@AdminUserID, 1),
  N'Волонтёрская суббота',
  N'<p>В эту субботу проводим <strong>уборку вольеров</strong> и прогулки с питомцами.</p><p>Приглашаем всех желающих помочь!</p><ol><li>Уборка территории</li><li>Выгул собак</li><li>Кормление животных</li></ol>',
  DATEADD(DAY, -20, GETDATE()), 1,
  'https://www.google.com/url?sa=i&url=https%3A%2F%2Fwww.eco-sniper.ru%2Fblogs%2Fdachnye-otvety%2F10-zhivotnyh-kotorye-prinosyat-polzu-dlya-sada-i-ogoroda&psig=AOvVaw2Ub850ahoPDFjZXEhZk9fe&ust=1761947202416000&source=images&cd=vfe&opi=89978449&ved=0CBUQjRxqFwoTCIiF0fvyzJADFQAAAAAdAAAAABAV'
WHERE NOT EXISTS (SELECT 1 FROM News WHERE Title = N'Волонтёрская суббота');

GO

USE AnimalShelterDB;

IF NOT EXISTS (SELECT 1 FROM Roles WHERE RoleName = 'Guest')
  INSERT INTO Roles (RoleName) VALUES ('Guest');

DECLARE @GuestUserID INT =
(
  SELECT TOP 1 u.UserID
  FROM Users u
  JOIN Roles r ON u.RoleID = r.RoleID
  WHERE r.RoleName = 'Guest'
  ORDER BY u.UserID
);

IF @GuestUserID IS NULL
BEGIN
  INSERT INTO Users (Email, PasswordHash, LastName, FirstName, MiddleName, Phone, RoleID)
  VALUES ('guest@test.local', 'test', N'Гость', N'Тест', NULL, '+79990000000',
          (SELECT RoleID FROM Roles WHERE RoleName='Guest'));
  SET @GuestUserID = SCOPE_IDENTITY();
END

INSERT INTO Messages (SenderID, ParentMessageID, SubjectMessages, MessageText, SendDate, IsRead, RecipientRole)
VALUES (@GuestUserID, NULL, N'Знакомство с Бимой', N'Здравствуйте! Готовы показать Биму в субботу?', GETDATE(), 0, 'Manager');

DECLARE @Root1 INT = SCOPE_IDENTITY();

INSERT INTO Messages (SenderID, ParentMessageID, SubjectMessages, MessageText, SendDate, IsRead, RecipientRole)
VALUES (@GuestUserID, @Root1, NULL, N'Уточняю время — давайте в 12:00.', DATEADD(MINUTE, 10, GETDATE()), 0, NULL);

INSERT INTO Messages (SenderID, ParentMessageID, SubjectMessages, MessageText, SendDate, IsRead, RecipientRole)
VALUES (@GuestUserID, NULL, N'Пожертвование', N'Спасибо за поддержку приюта!', DATEADD(MINUTE, 1, GETDATE()), 0, NULL);

DECLARE @Root2 INT = SCOPE_IDENTITY();

INSERT INTO Messages (SenderID, ParentMessageID, SubjectMessages, MessageText, SendDate, IsRead, RecipientRole)
VALUES (@GuestUserID, @Root2, NULL, N'Готов прислать чек, если нужно.', DATEADD(MINUTE, 12, GETDATE()), 0, NULL);

GO

IF NOT EXISTS (SELECT 1 FROM VaccinationTypes WHERE VaccinationName = 'Комплексная вакцинация (DHPPi)')
BEGIN
    INSERT INTO VaccinationTypes (VaccinationName, Description)
    VALUES ('Комплексная вакцинация (DHPPi)', N'Комплексная вакцинация против чумы, гепатита, парвовируса и парагриппа собак');
END

GO

IF NOT EXISTS (SELECT 1 FROM VaccinationTypes WHERE VaccinationName = 'Бешенство')
BEGIN
    INSERT INTO VaccinationTypes (VaccinationName, Description)
    VALUES ('Бешенство', N'Вакцинация против бешенства');
END

GO

IF NOT EXISTS (SELECT 1 FROM VaccinationTypes WHERE VaccinationName = 'Лептоспироз')
BEGIN
    INSERT INTO VaccinationTypes (VaccinationName, Description)
    VALUES ('Лептоспироз', N'Вакцинация против лептоспироза');
END

GO

IF NOT EXISTS (SELECT 1 FROM VaccinationTypes WHERE VaccinationName = 'Пироплазмоз')
BEGIN
    INSERT INTO VaccinationTypes (VaccinationName, Description)
    VALUES ('Пироплазмоз', N'Вакцинация против пироплазмоза (бабезиоза) собак');
END

GO

IF NOT EXISTS (SELECT 1 FROM VaccinationTypes WHERE VaccinationName = 'Клещевой энцефалит')
BEGIN
    INSERT INTO VaccinationTypes (VaccinationName, Description)
    VALUES ('Клещевой энцефалит', N'Вакцинация против клещевого энцефалита');
END

GO

IF NOT EXISTS (SELECT 1 FROM VaccinationTypes WHERE VaccinationName = 'Комплексная вакцинация для кошек')
BEGIN
    INSERT INTO VaccinationTypes (VaccinationName, Description)
    VALUES ('Комплексная вакцинация для кошек', N'Комплексная вакцинация против панлейкопении, ринотрахеита и калицивироза кошек');
END

GO

IF NOT EXISTS (SELECT 1 FROM VaccinationTypes WHERE VaccinationName = 'Бешенство (кошки)')
BEGIN
    INSERT INTO VaccinationTypes (VaccinationName, Description)
    VALUES ('Бешенство (кошки)', N'Вакцинация против бешенства для кошек');
END

GO

IF NOT EXISTS (SELECT 1 FROM VaccinationTypes WHERE VaccinationName = 'Лейкоз кошек (FeLV)')
BEGIN
    INSERT INTO VaccinationTypes (VaccinationName, Description)
    VALUES ('Лейкоз кошек (FeLV)', N'Вакцинация против вирусного лейкоза кошек');
END

GO

IF NOT EXISTS (SELECT 1 FROM VaccinationTypes WHERE VaccinationName = 'Хламидиоз кошек')
BEGIN
    INSERT INTO VaccinationTypes (VaccinationName, Description)
    VALUES ('Хламидиоз кошек', N'Вакцинация против хламидиоза кошек');
END

GO

IF NOT EXISTS (SELECT 1 FROM VaccinationTypes WHERE VaccinationName = 'Лишай (дерматофитоз)')
BEGIN
    INSERT INTO VaccinationTypes (VaccinationName, Description)
    VALUES ('Лишай (дерматофитоз)', N'Вакцинация против дерматофитоза (лишая)');
END

GO

