
# API Backend for Waste-to-Energy Processing

This repository contains the backend for a Waste-to-Energy processing application. The backend is built using Flask and provides multiple API endpoints for different waste processing methods such as **Fermentation**, **HTL (Hydrothermal Liquefaction)**, **Combustion**, and **Anaerobic Digestion**.

## Table of Contents
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Running the Application](#running-the-application)
- [API Endpoints](#api-endpoints)
- [Environment Variables](#environment-variables)
- [Docker Usage](#docker-usage)
- [Contributing](#contributing)
- [License](#license)

---

## Project Structure

```
/api-backend
│
├── /app
│   ├── /blueprints               # Contains Blueprints for each functional module
│   │   ├── fermentation.py        # Fermentation-related API routes
│   │   ├── htl.py                 # HTL-related API routes
│   │   ├── combustion.py          # Combustion-related API routes
│   │   └── digestion.py           # Digestion-related API routes
│   ├── /services                 # Business logic and data processing scripts
│   │   ├── fermentation_service.py
│   │   ├── htl_service.py
│   │   ├── combustion_service.py
│   │   └── digestion_service.py
│   ├── /data                     # Data files (CSV, Excel, etc.)
│   │   └── sludge_data_dmt.csv    # Sludge data for HTL functions   
│   ├── __init__.py               # App factory and Blueprint registration
│   └── config.py                 # Configuration for environment variables
│
├── Dockerfile                    # Dockerfile for containerizing the API
├── requirements.txt              # Python dependencies
├── .env                          # Environment variables for local development
└── wsgi.py                       # Entry point for WSGI server
```

### Key Components:
- **Blueprints**: Separate each API route into its module (e.g., fermentation, HTL, combustion, digestion).
- **Services**: Contains the business logic and data handling for each processing method.
- **Data**: Stores relevant CSV and other data files used in processing the requests.
- **Configuration**: Manages environment-specific settings through `config.py` and environment variables.

---

## Installation

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/your-username/api-backend.git
   cd api-backend
   ```

2. **Create and Activate a Virtual Environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate   # On macOS/Linux
   venv\Scripts\activate      # On Windows
   ```

3. **Install the Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set Up Environment Variables**:
   Create a `.env` file in the root directory and add your environment variables (e.g., `FLASK_ENV`, `SECRET_KEY`). You can use the `.env.example` as a template:
   ```bash
   FLASK_ENV=development
   SECRET_KEY=your-secret-key
   ```

---

## Running the Application

1. **Run the Flask App Locally**:
   ```bash
   flask run
   ```

   The app will be running on `http://127.0.0.1:5000/`.

2. **WSGI Server**:
   For production environments, use a WSGI server (e.g., Gunicorn) to run the app via `wsgi.py`.

   Example:
   ```bash
   gunicorn --bind 0.0.0.0:5000 wsgi:app
   ```

---

## API Endpoints

### 1. HTL (Hydrothermal Liquefaction)
- **GET** `/api/v1/htl/county/<countyname>`: Fetch HTL data for a given county.
- **GET** `/api/v1/htl/sludge?sludge=<value>&unit=<unit>`: Calculate diesel price and global warming potential based on sludge mass.

### 2. Fermentation
- **GET** `/api/v1/fermentation/county/<countyname>`: Fetch fermentation data for a given county.
- **GET** `/api/v1/fermentation/biomass?mass=<value>`: Calculate ethanol production based on biomass mass.

### 3. Combustion
- **GET** `/api/v1/combustion/county/<countyname>`: Fetch combustion data for a given county.
- **GET** `/api/v1/combustion/mass?mass=<value>`: Calculate electricity and emissions from feedstock.

### 4. Anaerobic Digestion
- **GET** `/api/v1/digestion/county/<countyname>`: Fetch anaerobic digestion data for a given county.
- **GET** `/api/v1/digestion/mass?mass=<value>`: Calculate biogas production based on feedstock mass.

---

## Environment Variables

- **FLASK_ENV**: Environment the app is running in (`development`, `testing`, `production`).
- **SECRET_KEY**: Secret key for Flask app.
- **DATABASE_URL**: If you add a database, configure the URL here.

You can add more environment-specific variables in your `.env` file.

---

## Docker Usage

1. **Build the Docker Image**:
   ```bash
   docker build -t api-backend .
   ```

2. **Run the Container**:
   ```bash
   docker run -p 5000:5000 api-backend
   ```

   This will run the app inside a Docker container and expose it on port 5000.

---

## Contributing

If you want to contribute to this project:

1. Fork the repository.
2. Create a feature branch (`git checkout -b feature/your-feature`).
3. Commit your changes (`git commit -m 'Add a new feature'`).
4. Push to the branch (`git push origin feature/your-feature`).
5. Open a pull request.

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

### Notes
- The app is configured to handle multiple routes and dynamically process data based on requests.
- Always ensure that the environment variables are set correctly, especially for production environments.
