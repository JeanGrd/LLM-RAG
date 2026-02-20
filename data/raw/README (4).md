# Olympic Games 📯

## Description

This project is an application for managing the Olympic Games, developed as part of a university project. It allows managing delegations, participants, sports infrastructures, events, spectators, tickets, and controllers. The application also provides functionalities to view results and the overall ranking.

## Technologies Used

- ☕ **Java 11**
- 🌱 **Spring Boot 2.5.4**
- 📦 **Spring Data JPA**
- 🐘 **Hibernate**
- 🍃 **Lombok**
- 🛠️ **Maven**
- 🗄️ **MySQL** (for in-memory testing)

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/JeanGrd/JeuxOlympique
   ```
2. Navigate to the project directory:
   ```bash
   cd your-repo
   ```
3. Compile and package the project:
   ```bash
   mvn clean package
   ```
4. Run the application:
   ```bash
   mvn spring-boot:run
   ```
5. Don't forget to fill in your MySQL properties in the application.properties file.

*Note: No web interface has been developed. If you want to try the application, you need to use an API platform like Postman.*

## Database Structure

### Main Entities

- **Delegation**: Represents a group participating in the games. Each delegation can have multiple participants.
- **Participant**: Represents an individual participating in events as part of a delegation.
- **Sports Infrastructure**: Represents the sports facilities where events are held.
- **Event**: Represents an event in the games.
- **Spectator**: Represents a spectator who can book tickets for events.
- **Ticket**: Represents a ticket booked by a spectator for an event.
- **Controller**: Represents a controller who validates tickets.
- **Participation**: Represents the participation of a delegation in an event.
- **Result**: Represents the result of a participant in an event.

## Conclusion

Developed as part of a university project, it leverages the power of Spring Boot and Spring Data JPA to ensure efficient and scalable operations. Through this project, we have gained valuable insights and hands-on experience in building robust backend systems.

## Credit

Written by:
- Ana PALEA
- Touria SAYAGH
- Jean GUIRAUD

Year of project completion: 2024
