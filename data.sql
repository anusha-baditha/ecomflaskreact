-- MySQL dump 10.13  Distrib 8.0.42, for Win64 (x86_64)
--
-- Host: localhost    Database: ecom22db
-- ------------------------------------------------------
-- Server version	8.0.42

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `admindata`
--

DROP TABLE IF EXISTS `admindata`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `admindata` (
  `adminid` binary(16) NOT NULL,
  `adminname` varchar(30) NOT NULL,
  `admin_email` varchar(50) NOT NULL,
  `admin_phoneno` varchar(10) DEFAULT NULL,
  `admin_password` varbinary(255) DEFAULT NULL,
  `admin_address` text,
  `admin_agree` enum('on','off') DEFAULT NULL,
  `admin_imgdata` varchar(15) DEFAULT NULL,
  PRIMARY KEY (`adminid`),
  UNIQUE KEY `admin_email` (`admin_email`),
  UNIQUE KEY `admin_email_2` (`admin_email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `admindata`
--

LOCK TABLES `admindata` WRITE;
/*!40000 ALTER TABLE `admindata` DISABLE KEYS */;
INSERT INTO `admindata` VALUES (_binary '\0\ q\Z\ÒΩ $LÜA$','anusha','anusha@codegnan.com','1234567890',_binary '$2b$12$eOV5R5Vu3jO8m9P/HypWY.vWj/kdjL9p.Ri1dGduU.1/.T.boEKQW','vijayawada pb siddhartha nagar ,61-9-80','on','Q2jF7o.webp'),(_binary 'IkÜM\Ù\Ò∞ﬁú¸ËõÜU','anusha','lakshmi.sri401@gmail.com',NULL,_binary '$2b$12$nS2aTF9T5vslRXVnS4PciuVjFfvV1T4qSVYo.cciFZpNI3YeSpRzO','abx','on',NULL);
/*!40000 ALTER TABLE `admindata` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `cart`
--

DROP TABLE IF EXISTS `cart`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `cart` (
  `cartid` binary(16) NOT NULL,
  `itemid` binary(16) DEFAULT NULL,
  `userid` binary(16) DEFAULT NULL,
  `quantity` int DEFAULT NULL,
  PRIMARY KEY (`cartid`),
  KEY `itemid` (`itemid`),
  KEY `userid` (`userid`),
  CONSTRAINT `cart_ibfk_1` FOREIGN KEY (`itemid`) REFERENCES `items` (`itemid`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `cart_ibfk_2` FOREIGN KEY (`userid`) REFERENCES `userdata` (`userid`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `cart`
--

LOCK TABLES `cart` WRITE;
/*!40000 ALTER TABLE `cart` DISABLE KEYS */;
INSERT INTO `cart` VALUES (_binary '\\§-≠Nã\ÒíIú¸ËõÜU',_binary '\—(¸\ÂM\˜\Ò∞ﬁú¸ËõÜU',_binary '\Œ*\r∂NÜ\ÒíIú¸ËõÜU',5);
/*!40000 ALTER TABLE `cart` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `items`
--

DROP TABLE IF EXISTS `items`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `items` (
  `itemid` binary(16) NOT NULL,
  `itemname` longtext,
  `item_desc` longtext,
  `item_about` longtext,
  `price` decimal(10,2) DEFAULT NULL,
  `quantity` bigint DEFAULT NULL,
  `category` enum('home_appliences','Grocery','Fashion','Electronics','Sports','toys') DEFAULT NULL,
  `added_by` binary(16) DEFAULT NULL,
  `item_img` varchar(20) DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`itemid`),
  KEY `added_by` (`added_by`),
  CONSTRAINT `items_ibfk_1` FOREIGN KEY (`added_by`) REFERENCES `admindata` (`adminid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `items`
--

LOCK TABLES `items` WRITE;
/*!40000 ALTER TABLE `items` DISABLE KEYS */;
INSERT INTO `items` VALUES (_binary '`E\"π\ÒÖ{ $LÜA$','SKMEI Men\'s Analog Sports Watch Waterproof Led Men\'s Watch New Wheels Rolling Creative Fashion Wristwatch 2359','Case diameter4.21 Centimetres\r\nBand colourGreen\r\nBand material typeSilica Gel\r\nWarranty typeLimited\r\nWatch movement typeQuartz\r\nItem weight84.4 Grams\r\nCountry of OriginChina','Premium Build & Comfort ‚Äì Crafted with a zinc alloy case, durable glass crystal, and an adjustable silicone strap for a sleek and comfortable fit.\r\n',2035.00,3000,'Fashion',_binary '\0\ q\Z\ÒΩ $LÜA$','Z8lS1z.jpg','2026-03-18 16:26:02'),(_binary '0è~˛\"π\ÒÖ{ $LÜA$','VOLTURI Air Tight Kitchen Containers Set of 6, Kitchen Storage Box for Pulses, Cereals, Grains, Dry Fruits, Pantry Organization, Kitchen Accessories Items for Home, Food Grade (1200 ML, Transparent)','\r\nBrand	VOLTURI\r\nColour	ATC-1200\r\nMaterial	Polypropylene\r\nMaterial Feature	Food Grade, Freezer Safe, Recyclable, Resistant to acidic and alkaline substances, oils, and fats that are present in food.Food Grade, Freezer Safe, Recyclable, Resistant to acidic and alkaline substances, oils, and fats that are present in food.\r\nCapacity	1200 Milliliters\r\n','Ideal Size & Versatile Use: VOLTURI containers for kitchen storage have three convenient sizes ‚Äì 500 ML, 1200 ML, and 1500 ML ‚Äì providing flexible containers for kitchen storage set options for a variety of kitchen staples. From snacks to bulk grains, these kitchen storage have you covered.\r\nVersatile & Multi-Purpose: VOLTURI Air Tight kitchen storage box boast a precision-sealed design, ensuring your pulses, cereals, grains, and more stay fresher for longer, preserving their flavor and nutritional value.\r\nSafe & Durable Material: Crafted from high-quality, food-grade materials, these container boxes for storage are BPA-free, guaranteeing the safety of your food. Keep your kitchen accessories items for home free from harmful chemicals while maintaining the freshness of your ingredients.',500.00,45000,'home_appliences',_binary '\0\ q\Z\ÒΩ $LÜA$','F7gR3z.jpg','2026-03-18 16:27:00'),(_binary '•`>ç\…\ÒÖ{ $LÜA$','Vasukie Panda Coffee Mug ','Brand	Vasukie\r\nMaterial	Ceramic\r\nColour	Bear Mug\r\nCapacity	420 Milliliters\r\nSpecial Feature	Dishwasher Safe, Microwave Safe\r\nStyle	Antique\r\nTheme	Cartoon\r\nRecommended Uses For Product	Home, Office\r\nIncluded Components	Lid, Straw\r\nSpecific Uses For Product	Cold Drinks, Hot Drinks\r\n','About this item\r\nHIGH QUALITY-- Our cute Panda Mark cup is made of high-quality ceramics, healthy material, contains a lovely lid ,a kawaii coaster and a Glass spoon. This cute cup with 3D Panda lightweight lid has excellent heat insulation properties and can keep your coffee or tea warm or cool\r\nPersonality Cute Panda Mug Design-- This ceramic Panda cup has a lovely pattern and exquisite body design, which is beautiful and easy to handle; Big capacity 420 ML, the cup mouth is rounded for easy drinking, the large handle is comfortable to hold.',566.00,56,'home_appliences',_binary '\0\ q\Z\ÒΩ $LÜA$','C4zN5c.webp','2026-03-13 16:14:43'),(_binary '\—(¸\ÂM\˜\Ò∞ﬁú¸ËõÜU','car','cardesc','c about',500.00,23,'Fashion',_binary 'IkÜM\Ù\Ò∞ﬁú¸ËõÜU','L3qU1w.png','2026-05-12 17:13:38');
/*!40000 ALTER TABLE `items` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `order_items`
--

DROP TABLE IF EXISTS `order_items`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `order_items` (
  `order_detailsid` int unsigned NOT NULL AUTO_INCREMENT,
  `orderid` int unsigned DEFAULT NULL,
  `itemid` binary(16) NOT NULL,
  `item_name` longtext,
  `item_price` decimal(10,2) DEFAULT NULL,
  `item_quantity` int unsigned DEFAULT NULL,
  `subtotal` decimal(10,2) DEFAULT NULL,
  `item_category` enum('home_appliences','Grocery','Fashion','Electronics','Sports','toys') DEFAULT NULL,
  `item_filename` varchar(20) DEFAULT NULL,
  PRIMARY KEY (`order_detailsid`),
  KEY `itemid` (`itemid`),
  CONSTRAINT `order_items_ibfk_1` FOREIGN KEY (`itemid`) REFERENCES `items` (`itemid`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `order_items`
--

LOCK TABLES `order_items` WRITE;
/*!40000 ALTER TABLE `order_items` DISABLE KEYS */;
INSERT INTO `order_items` VALUES (1,3,_binary '0è~˛\"π\ÒÖ{ $LÜA$','VOLTURI Air Tight Kitchen Containers Set of 6, Kitchen Storage Box for Pulses, Cereals, Grains, Dry Fruits, Pantry Organization, Kitchen Accessories Items for Home, Food Grade (1200 ML, Transparent)',500.00,1,500.00,'home_appliences','F7gR3z.jpg'),(2,3,_binary '•`>ç\…\ÒÖ{ $LÜA$','Vasukie Panda Coffee Mug ',566.00,1,566.00,'home_appliences','C4zN5c.webp'),(3,4,_binary '0è~˛\"π\ÒÖ{ $LÜA$','VOLTURI Air Tight Kitchen Containers Set of 6, Kitchen Storage Box for Pulses, Cereals, Grains, Dry Fruits, Pantry Organization, Kitchen Accessories Items for Home, Food Grade (1200 ML, Transparent)',500.00,1,500.00,'home_appliences','F7gR3z.jpg'),(4,5,_binary '`E\"π\ÒÖ{ $LÜA$','SKMEI Men\'s Analog Sports Watch Waterproof Led Men\'s Watch New Wheels Rolling Creative Fashion Wristwatch 2359',2035.00,1,2035.00,'Fashion','Z8lS1z.jpg'),(5,5,_binary '0è~˛\"π\ÒÖ{ $LÜA$','VOLTURI Air Tight Kitchen Containers Set of 6, Kitchen Storage Box for Pulses, Cereals, Grains, Dry Fruits, Pantry Organization, Kitchen Accessories Items for Home, Food Grade (1200 ML, Transparent)',500.00,1,500.00,'home_appliences','F7gR3z.jpg'),(6,6,_binary '0è~˛\"π\ÒÖ{ $LÜA$','VOLTURI Air Tight Kitchen Containers Set of 6, Kitchen Storage Box for Pulses, Cereals, Grains, Dry Fruits, Pantry Organization, Kitchen Accessories Items for Home, Food Grade (1200 ML, Transparent)',500.00,1,500.00,'home_appliences','F7gR3z.jpg');
/*!40000 ALTER TABLE `order_items` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `orders`
--

DROP TABLE IF EXISTS `orders`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `orders` (
  `orderid` int unsigned NOT NULL AUTO_INCREMENT,
  `razorpay_ordid` varchar(100) DEFAULT NULL,
  `razorpay_payment` varchar(100) DEFAULT NULL,
  `userid` binary(16) DEFAULT NULL,
  `total_amount` decimal(10,2) DEFAULT NULL,
  `delivery` int unsigned DEFAULT NULL,
  `tax` decimal(10,2) DEFAULT NULL,
  `grand_total` decimal(10,2) DEFAULT NULL,
  `status` varchar(30) DEFAULT 'paid',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`orderid`),
  KEY `userid` (`userid`),
  CONSTRAINT `orders_ibfk_1` FOREIGN KEY (`userid`) REFERENCES `userdata` (`userid`)
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `orders`
--

LOCK TABLES `orders` WRITE;
/*!40000 ALTER TABLE `orders` DISABLE KEYS */;
INSERT INTO `orders` VALUES (3,'order_SV1oGbCKl1YOiO','pay_SV1ok9YETJ5qKL',_binary '5\\Ó!\Ó\ÒÖ{ $LÜA$',1066.00,40,53.30,1159.30,'paid','2026-03-24 15:53:05'),(4,'order_SVQjC1jdPraepD','pay_SVQjW4AFzAgUXF',_binary '5\\Ó!\Ó\ÒÖ{ $LÜA$',500.00,40,25.00,565.00,'paid','2026-03-25 16:15:27'),(5,'order_SVQpnLbYGEKngR','pay_SVQq4ux0mNC5zX',_binary '5\\Ó!\Ó\ÒÖ{ $LÜA$',2535.00,40,126.75,2701.75,'paid','2026-03-25 16:21:39'),(6,'order_SVQqUAvye52mUi','pay_SVQqqBMcc42ETp',_binary '5\\Ó!\Ó\ÒÖ{ $LÜA$',500.00,40,25.00,565.00,'paid','2026-03-25 16:22:23');
/*!40000 ALTER TABLE `orders` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `reviews`
--

DROP TABLE IF EXISTS `reviews`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `reviews` (
  `r_id` int unsigned NOT NULL AUTO_INCREMENT,
  `r_text` varchar(255) DEFAULT NULL,
  `rating` enum('1','2','3','4','5') DEFAULT NULL,
  `itemid` binary(16) DEFAULT NULL,
  `userid` binary(16) DEFAULT NULL,
  PRIMARY KEY (`r_id`),
  KEY `itemid` (`itemid`),
  KEY `userid` (`userid`),
  CONSTRAINT `reviews_ibfk_1` FOREIGN KEY (`itemid`) REFERENCES `items` (`itemid`) ON DELETE SET NULL,
  CONSTRAINT `reviews_ibfk_2` FOREIGN KEY (`userid`) REFERENCES `userdata` (`userid`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `reviews`
--

LOCK TABLES `reviews` WRITE;
/*!40000 ALTER TABLE `reviews` DISABLE KEYS */;
INSERT INTO `reviews` VALUES (1,'avg ','3',_binary '0è~˛\"π\ÒÖ{ $LÜA$',_binary '5\\Ó!\Ó\ÒÖ{ $LÜA$');
/*!40000 ALTER TABLE `reviews` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `userdata`
--

DROP TABLE IF EXISTS `userdata`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `userdata` (
  `userid` binary(16) NOT NULL,
  `username` varchar(20) NOT NULL,
  `useremail` varchar(50) NOT NULL,
  `password` varbinary(255) DEFAULT NULL,
  `useraddress` text NOT NULL,
  `usergender` enum('male','female','others') DEFAULT NULL,
  `userphone` varchar(20) DEFAULT NULL,
  PRIMARY KEY (`userid`),
  UNIQUE KEY `useremail` (`useremail`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `userdata`
--

LOCK TABLES `userdata` WRITE;
/*!40000 ALTER TABLE `userdata` DISABLE KEYS */;
INSERT INTO `userdata` VALUES (_binary '5\\Ó!\Ó\ÒÖ{ $LÜA$','anusha Baditha','anusha@codegnan.com',_binary '$2b$12$66W18oOn2Rtln3YvixnAOuya1T9T45CEWR1K4OKZBKmEQrMiJ8l7i','vijayawada pb siddhartha nagar ,61-9-80','female','12312312312'),(_binary '\Œ*\r∂NÜ\ÒíIú¸ËõÜU','Lakshmi','lakshmi.sri401@gmail.com',_binary '$2b$12$5xkF7ToxbDvfkeY/cTYtZ.cXkM/ITmlqvcooCNElc03NGBmD182Ae','Hyderabad','female','9876543210');
/*!40000 ALTER TABLE `userdata` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-05-15 18:17:52
