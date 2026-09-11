# DiabCare AI - Diabetic Foot Screening Application

AI-Powered Diabetic Foot Early Warning System - From a simple photograph to an early warning.

## Project Structure

```
diabcare-ai/
├── backend/
│   ├── app.py              # Flask API server
│   ├── database.py         # SQLite database operations
│   ├── reports.py          # PDF report generation
│   └── model/
│       └── inference.py    # ML model inference
├── frontend/
│   ├── index.html          # Main UI
│   ├── css/style.css       # Styling
│   └── js/app.js           # Frontend logic
├── data/
│   ├── scans/              # Uploaded images
│   └── reports/            # Generated PDFs
├── requirements.txt        # Python dependencies
└── README.md               # This file
```

## Setup Instructions

### 1. Install Python Dependencies

```bash
cd diabcare-ai
pip install -r requirements.txt
```

### 2. Run the Application

```bash
cd backend
python app.py
```

The application will start at: **http://localhost:5000**

### 3. Access the Application

Open your browser and go to: `http://localhost:5000`

## Features

- **Image Upload**: Drag & drop or click to upload foot photographs
- **AI Analysis**: YOLOv8 classification model for ulcer detection
- **Risk Assessment**: LOW / MEDIUM / HIGH / UNCERTAIN risk levels
- **Scan History**: Track all previous scans with timestamps
- **PDF Reports**: Downloadable screening reports
- **Dashboard**: Overview of scan statistics

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/analyze | Analyze an image |
| GET | /api/history | Get all scans |
| GET | /api/scan/:id | Get specific scan |
| DELETE | /api/scan/:id | Delete a scan |
| GET | /api/report/:id | Download PDF report |
| GET | /api/stats | Get statistics |
| GET | /api/image/:filename | Get image file |

## Model

The application uses YOLOv8 classification. For demo purposes, it uses a pretrained model. To use a custom trained model:

1. Train a YOLOv8 classification model on diabetic foot dataset
2. Save the weights as `best.pt`
3. Place the file in `backend/model/best.pt`

## Important Notes

- This is a **screening tool**, not a medical diagnosis
- Always consult healthcare professionals for proper evaluation
- Results should be interpreted by qualified medical personnel
