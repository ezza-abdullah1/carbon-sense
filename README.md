# CarbonSense

Urban carbon emission forecasting and monitoring platform for Lahore, Pakistan.

## Problem

Fragmented emission monitoring across sectors prevents effective climate action in rapidly urbanizing cities like Lahore.

## Solution

CarbonSense is a web-based platform integrating Climate TRACE data with AI-powered forecasting and policy recommendations across five sectors: Transportation, Industry, Energy, Buildings, and Waste.

## Key Features

- Multi-sector emission analysis: Historical data visualization for all sectors
- AI forecasting: SARIMA-based predictions (2.42% MAPE accuracy)
- Interactive maps: Geographic hotspot identification using Leaflet.js
- Smart recommendations: RAG-powered mitigation strategies
- Report generation: Exportable PDF/CSV analytics reports

## Tech Stack

**Frontend:** React.js, Redux Toolkit, Chart.js, Leaflet.js  
**Backend:** Django 4.2+, Django REST Framework  
**ML/Analytics:** Python 3.10+, PyTorch, statsmodels, scikit-learn  
**Database:** PostgreSQL 15+, Redis 7+, pgvector  
**Deployment:** Docker, Nginx, Gunicorn

## Installation

Clone repository
git clone https://github.com/ezza-abdullah1/carbon-sense.git
cd carbon-sense

Install dependencies
npm install

Run development server
npm run dev

## Data Source

Climate TRACE - Over 79,815 global emission sources monitored via more than 300 satellites

## Results

- Forecasting accuracy: 2.42% MAPE (SARIMA model)
- Coverage: 56 months historical data (2021-2025)
- Validation: R² = 0.70 on test set
- Geographic resolution: 30-meter spatial analysis

## Architecture

┌─────────────────┐
│ React Frontend │
│ (Dashboard) │
└────────┬────────┘
│
┌────────▼────────┐
│ Django Backend │
│ (REST API) │
└────────┬────────┘
│
┌────────▼────────┐
│ ML Services │
│ (SARIMA + RAG) │
└────────┬────────┘
│
┌────────▼────────┐
│ PostgreSQL/Redis│
│ (Data Layer) │
└─────────────────┘

## Use Cases

- Government policy planning
- Urban emission hotspot identification
- Climate action progress tracking
- Environmental impact assessment
