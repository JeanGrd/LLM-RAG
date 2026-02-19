# Factory Simulation in Java

Author: Jean Guiraud

License: This code is free and open for anyone to use and modify.

## Description

This project simulates a factory where workers and delivery drivers work together to produce and deliver products. The factory has limited storage space for components and uses separate threads to model workers and delivery drivers. The factory also employs a foreman who monitors the status of the workers and drivers periodically.

The main components of the simulation are:

- `Bac`: A class representing storage containers for different components.
- `Usine`: A class representing the factory, which contains the storage containers.
- `Livreur`: A class representing the delivery drivers who supply components to the factory.
- `Ouvrier`: A class representing the workers who assemble the products.
- `Palette`: A class representing a pallet for storing finished products.
- `ContreMaitre`: A class representing a foreman who periodically interrupts workers and drivers to check their status.

## Usage

To run the simulation, compile and execute the `main.java` file. The program will display the progress of workers and drivers as they complete their tasks. The simulation can be stopped by terminating the program.

## Customization

The simulation can be customized by modifying the parameters of the `Usine`, `Livreur`, and `Ouvrier` instances created in the `main.java` file. You can adjust the number of storage containers, the types and quantities of components delivered, and the types of products produced by the workers.

## Contributing

Contributions are welcome! If you find any issues or would like to suggest improvements, please feel free to open an issue or submit a pull request.

