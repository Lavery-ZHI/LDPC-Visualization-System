# LDPC Visualization System

An interactive LDPC (Low-Density Parity-Check) code visualization and simulation system featuring a Flutter cross-platform frontend and Python FastAPI backend.

## 📋 Features

- **Interactive Tanner Graph Editor**: Drag-and-drop construction of LDPC codes
- **Multiple Decoding Algorithms**: Min-Sum and Sum-Product belief propagation
- **Channel Simulation**: AWGN and BSC channel models
- **Real-time BER Analysis**: Monte Carlo simulation with live performance curves
- **Cross-platform Support**: Web, Windows, Android, and iOS
- **Matrix Visualization**: Interactive H-matrix and G-matrix viewers
- **Template Library**: Pre-built LDPC code templates

## 🏗️ Architecture

```
LDPC-Visualization-System/
├── backend/                 # Python FastAPI backend
│   ├── algorithms/         # Core LDPC algorithms
│   ├── models/            # Data models and validation
│   ├── services/          # Background services
│   └── utils/             # Utility functions
└── my_ldpc_app/           # Flutter frontend
    ├── lib/
    │   ├── providers/     # State management
    │   ├── services/      # API communication
    │   ├── widgets/       # UI components
    │   └── screens/       # Application screens
    └── web/               # Web build assets
```

## 🚀 Quick Start

### Backend Setup

1. **Navigate to backend directory**:
   ```bash
   cd backend
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Start the server**:
   ```bash
   python main.py
   ```
   Server runs on http://127.0.0.1:9999

### Frontend Setup

1. **Navigate to Flutter app**:
   ```bash
   cd my_ldpc_app
   ```

2. **Install dependencies**:
   ```bash
   flutter pub get
   ```

3. **Run the application**:
   ```bash
   flutter run -d chrome    # For web
   flutter run -d windows   # For Windows desktop
   ```

### Quick Start Script

For Windows users, use the batch file:
```bash
start_full_app.bat
```

## 📊 Core Algorithms

### LDPC Encoding
- Systematic encoding with generator matrix computation
- Sparse matrix optimization for large codes
- Gaussian elimination over GF(2)

### LDPC Decoding
- **Min-Sum Algorithm**: Fast approximation with scaling factors
- **Sum-Product Algorithm**: Optimal belief propagation
- Early termination via syndrome checking
- Configurable iteration limits and convergence thresholds

### Simulation Engine
- Monte Carlo BER/FER analysis
- Multiple SNR point simulation
- Real-time progress tracking
- Early stopping criteria for efficient simulation

## 🔧 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/encode` | POST | Generate LDPC code from graph or matrix |
| `/api/v1/decode` | POST | Decode received codeword with channel LLR |
| `/api/simulate` | POST | Run complete BER simulation |
| `/api/quick-test` | POST | Single SNR point rapid testing |
| `/api/matrix-templates` | GET | Available LDPC matrix templates |

## 📱 Frontend Features

- **Responsive Design**: Adaptive layouts for different screen sizes
- **Interactive Canvas**: Real-time graph editing with visual feedback
- **Live Charts**: BER performance curves using FL Chart
- **Material Design**: Modern UI following Material Design principles
- **Cross-platform**: Single codebase for multiple platforms

## 🧪 Testing

### Backend Tests
```bash
cd backend
python -m pytest tests/                    # All tests
python -m pytest tests/unit/              # Unit tests
python -m pytest tests/integration/       # Integration tests
python -m pytest tests/performance/       # Performance tests
```

### Frontend Tests
```bash
cd my_ldpc_app
flutter test                              # Widget tests
```

## 📄 Documentation

- [Technical Documentation](LDPC可视化编解码仿真系统详细技术文档.md)
- [Source Code Appendix](Appendix_A_Source_Code.md)
- [Development Guide](CLAUDE.md)

## 🛠️ Technologies Used

### Backend
- **FastAPI**: Modern Python web framework
- **NumPy/SciPy**: Scientific computing and sparse matrices
- **Pydantic**: Data validation and settings management
- **Uvicorn**: ASGI server implementation

### Frontend
- **Flutter**: Cross-platform UI framework
- **Provider**: State management solution
- **Dio**: HTTP client for API communication
- **FL Chart**: Data visualization library

## 📈 Performance

- **Matrix Operations**: Optimized sparse matrix algorithms
- **Memory Efficiency**: Lazy evaluation and caching
- **Simulation Speed**: Multi-threaded processing support
- **Real-time Updates**: WebSocket-based progress streaming

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is developed for academic research purposes.

## 📧 Contact

Project Link: [https://github.com/[your-username]/LDPC-Visualization-System](https://github.com/[your-username]/LDPC-Visualization-System)

## 🙏 Acknowledgments

- LDPC coding theory research community
- Flutter and FastAPI development teams
- Scientific Python ecosystem contributors