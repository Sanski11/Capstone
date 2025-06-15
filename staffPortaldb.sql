drop database staff_portal
;

create database staff_portal
;

USE `staff_portal`
;

DROP TABLE IF EXISTS `users`;
CREATE TABLE `users` (
  `user_id` int NOT NULL,
  `username` varchar(45) DEFAULT NULL,
  `email` varchar(45) DEFAULT NULL,
  `password` varchar(45) DEFAULT NULL,
  `role` varchar(45) DEFAULT NULL,
  PRIMARY KEY (`user_id`)
) 
;

/****** Object:  Table `Guest`    Script Date: 08/06/2025 8:46:24 am ******/
DROP TABLE IF EXISTS `Guest`;
CREATE TABLE `Guest`(
	`guest_id` int AUTO_INCREMENT NOT NULL,
	`first_name` varchar(50) NOT NULL,
	`middle_name` varchar(50) NULL,
	`last_name` varchar(50) NOT NULL,
	`email` varchar(100) NOT NULL,
	`phone` varchar(15) NULL,
 PRIMARY KEY (
	`guest_id` ASC
)
)
;


/****** Object:  Table `Room`    Script Date: 08/06/2025 8:46:25 am ******/
DROP TABLE IF EXISTS `Room`;
CREATE TABLE `Room`(
	`room_id` int AUTO_INCREMENT NOT NULL,
	`room_number` varchar(10) NOT NULL,
	`room_type` varchar(20) NULL,
	`room_status` varchar(20) NOT NULL,
 PRIMARY KEY (
	`room_id` ASC
)
)
;
/****** Object:  Table `Services`    Script Date: 08/06/2025 8:46:25 am ******/
DROP TABLE IF EXISTS `Services`;
CREATE TABLE `Services`(
	`service_id` int AUTO_INCREMENT NOT NULL,
	`service_type` varchar(20) NOT NULL,
	`item` varchar(100) NULL,
	`amount` decimal(10, 2) NOT NULL,
 PRIMARY KEY (
	`service_id` ASC
)
)
;
/****** Object:  Table `Staff`    Script Date: 08/06/2025 8:46:25 am ******/
DROP TABLE IF EXISTS `Staff`;
CREATE TABLE `Staff`(
	`staff_id` int AUTO_INCREMENT NOT NULL,
	`first_name` varchar(50) NOT NULL,
	`last_name` varchar(50) NOT NULL,
	`role` varchar(50) NOT NULL,
	`email` varchar(100) NOT NULL,
	`phone` varchar(15) NULL,
 PRIMARY KEY (
	`staff_id` ASC
)
)
;
;

DROP TABLE IF EXISTS `bookings`;
CREATE TABLE `bookings` (
  `booking_id` int NOT NULL AUTO_INCREMENT,
  `guest_id` int NOT NULL,
  `room_type` varchar(20) NOT NULL,
  `room_id` int DEFAULT NULL,
  `exp_check_in` date NOT NULL,
  `exp_check_out` date NOT NULL,
  `actual_check_in` date DEFAULT NULL,
  `actual_check_out` date DEFAULT NULL,
  `status` varchar(50) DEFAULT NULL,
  PRIMARY KEY (`booking_id`)
) 
;
/****** Object:  Table `RoomGuest`    Script Date: 08/06/2025 8:46:25 am ******/
DROP TABLE IF EXISTS `RoomGuest`;
CREATE TABLE `RoomGuest`(
	`roomGuest_id` int AUTO_INCREMENT NOT NULL,
	`room_id` int NOT NULL,
	`guest_id` int NOT NULL,
	`checkin_date` datetime NOT NULL,
	`checkout_date` datetime NULL,
 PRIMARY KEY (
	`roomGuest_id` ASC
)
)
;

/****** Object:  Table `Requests`    Script Date: 08/06/2025 8:46:25 am ******/
DROP TABLE IF EXISTS `Requests`;
CREATE TABLE `requests` (
  `request_id` int NOT NULL AUTO_INCREMENT,
  `booking_id` int NOT NULL,
  `service_id` int NOT NULL,
  `quantity` int NOT NULL,
  `unitCost` decimal(10,2) NOT NULL,
  `totalCost` decimal(10,2) NOT NULL,
  `status` varchar(20) NOT NULL,
  `request_time` datetime NOT NULL,
  `staff_id` int DEFAULT NULL,
  `completionTime` datetime DEFAULT NULL,
  PRIMARY KEY (`request_id`),
  KEY `FK_Requests_Booking_idx` (`booking_id`),
  KEY `FK_Requests_Staff_idx` (`staff_id`),
  KEY `FK_Requests_Service_idx` (`service_id`),
  CONSTRAINT `FK_Requests_Booking` FOREIGN KEY (`booking_id`) REFERENCES `bookings` (`booking_id`),
  CONSTRAINT `FK_Requests_Service` FOREIGN KEY (`service_id`) REFERENCES `services` (`service_id`),
  CONSTRAINT `FK_Requests_Staff` FOREIGN KEY (`staff_id`) REFERENCES `staff` (`staff_id`)
) 
;


-- USERS table
INSERT INTO `users` VALUES (1,'patrynne','asdf@asdf.com','patrynne','admin');

-- GUEST table
INSERT INTO Guest (guest_id, first_name, middle_name, last_name, email, phone) VALUES
(1, 'Patrynne', 'Dela Cruz', 'Lucas', 'lucaspatrynne@gmail.com', '09298376248'),
(2, 'Gina Lyn', 'Dela Cruz', 'Lucas', 'mukha73@yahoo.com', '09290851598'),
(3, 'Juan', 'Dela', 'Cruz', 'blablabla@gmail.com', '12345678901'),
(4, 'Shanna', 'Hazel', 'Palomo', 'shannahazelpalomo@benilde.edu.ph', '9283726499581'),
(5, 'La Salle', 'College', 'Benilde', 'dlscsb@yahoo.com', '18275033857'),
(6, 'Hello', 'Hi', 'Lord', 'gsgdgfd@yahoo.com', '123456788910'),
(7, 'Juan', 'Dela Cruz', 'Ulit', 'asdf@yahoo.com', '091827638');

-- ROOM table
INSERT INTO Room (room_id, room_number, room_type, room_status) VALUES
(1, '1001', 'Standard Twin Room', 'Vacant'),
(2, '1002', 'Standard Twin Room', 'Vacant'),
(3, '2001', 'Standard Double Room', 'Vacant'),
(4, '2002', 'Standard Double Room', 'Vacant'),
(5, '3001', 'Premium Twin Room', 'Vacant'),
(6, '3002', 'Premium Double Room', 'Vacant'),
(7, '4001', 'Family Room', 'Vacant'),
(8, '4002', 'Family Room', 'Vacant'),
(9, '4003', 'Family Room', 'Vacant');

-- ROOMGUEST table
INSERT INTO RoomGuest (roomGuest_id, room_id, guest_id, checkin_date, checkout_date) VALUES
(1, 1, 1, '2025-01-01', '2025-02-01'),
(2, 2, 2, '2024-10-03', '2024-01-03'),
(3, 3, 3, '2021-12-03', '2022-07-07'),
(4, 4, 4, '2018-12-04', '2018-12-12'),
(5, 5, 5, '2017-01-02', '2017-12-12'),
(6, 2, 2, '2012-11-11', '2012-12-11'),
(9, 5, 5, '2025-06-27', '2025-06-23');

-- SERVICES table
INSERT INTO Services (service_id, service_type, item, amount) VALUES
(1, 'Housekeeping', 'Towel Replacement', 120.00),
(2, 'Dining', 'Rib eye steak', 3800.00),
(3, 'Massage', 'Swedish 1 hr', 1200.00),
(4, 'Laundry', '1 kg', 150.00),
(6, 'Dining', 'Adobo', 3000.00),
(7, 'Housekeeping', 'Assistance with airconditioning', 0.00),
(8, 'Housekeeping', 'Assistance with using TV or remote control', 0.00),
(9, 'Housekeeping', 'Extra bed', 1500.00),
(10, 'Dining', 'Mango juice', 250.00),
(11, 'Dining', 'Red win', 300.00),
(12, 'Laundry', '2 kgs', 250.00),
(13, 'Laundry', '3 kgs', 500.00),
(14, 'Massage', 'Swedish 1/2 hr', 800.00),
(15, 'Massage', 'Shiatsu 1/2 hr', 800.00),
(16, 'Massage', 'Shiatsu 1 hr', 1200.00);

-- STAFF table
INSERT INTO Staff (staff_id, first_name, last_name, role, email, phone) VALUES
(1, 'Patrynne', 'Lucas', 'Housekeeper', 'patrynne.lucas@benilde.edu.ph', '09298376248'),
(2, 'Miguel', 'Aujero', 'Manager', 'miguel.aujero@benilde.edu.ph', '09290851598'),
(3, 'Shanan', 'Palomo', 'Manager', 'shanna.palomo@benilde.edu.ph', '09298374651'),
(4, 'Joseph', 'Villamin', 'Housekeeper', 'joseph.villamin@benilde.edu.ph', '09291345978'),
(5, 'Juan', 'Dela Cruz', 'Housekeeper', 'juan.delacruz@benilde.edu.ph', '09293857111'),
(6, 'Amelia', 'Adler', 'Manager', 'aadler@gmail.com', '88827345');

-- BOOKINGS table
INSERT INTO `bookings` VALUES (1,3,'Family Room',7,'2025-07-01','2025-07-03',NULL,NULL,'Confirmed');
INSERT INTO `bookings` VALUES (2,2,'Family Room',8,'2025-07-03','2025-07-05',NULL,NULL,'Confirmed');
INSERT INTO `bookings` VALUES (3,2,'Family Room',9,'2025-07-06','2025-07-07',NULL,NULL,'Confirmed');

-- REQUESTS table
INSERT INTO Requests (request_id, booking_id, service_id, quantity, unitCost, totalCost, status, request_time) VALUES
(1, 1, 1, 100, 50.00, 5000.00, 'Pending', '2025-06-06 14:30:00');



ALTER TABLE `Room` MODIFY `room_status` VARCHAR(20) DEFAULT 'Vacant';
ALTER TABLE `Requests`
ADD CONSTRAINT `FK_Requests_Services` FOREIGN KEY (`service_id`) REFERENCES `Services` (`service_id`);
;
ALTER TABLE `RoomGuest`
ADD  CONSTRAINT `FK_RoomGuest_Guest` FOREIGN KEY (`guest_id`) REFERENCES `Guest` (`guest_id`);
;