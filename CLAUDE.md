# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an LDPC (Low-Density Parity-Check) code visualization and simulation system with a Flutter frontend and Python FastAPI backend. The system provides graphical design, simulation, and optimization capabilities for LDPC codes.

## Development Commands

### Backend (Python FastAPI)
```bash
# Install dependencies
cd backend
pip install -r requirements.txt

# Start backend server
python main.py
# Server runs on http://127.0.0.1:9999 (port configurable in main.py)
# API documentation: http://127.0.0.1:9999/docs

# Run tests
python -m pytest tests/                    # All tests
python -m pytest tests/unit/              # Unit tests only
python -m pytest tests/integration/       # Integration tests only
python -m pytest tests/performance/       # Performance tests only

# Individual test files
python -m pytest tests/unit/test_encoder.py
python -m pytest tests/unit/test_decoder.py
```

### Frontend (Flutter)
```bash
# Install dependencies
cd my_ldpc_app
flutter pub get

# Start development server
flutter run -d chrome          # Web version
flutter run -d windows         # Windows desktop
flutter run -d android         # Android (if emulator running)

# Build for production
flutter build web              # Web build
flutter build windows         # Windows build

# Run widget tests
flutter test
```

### Quick Start Scripts
```bash
# Windows: Complete application startup
start_full_app.bat

# Windows: Alternative startup (in my_ldpc_app/)
start_app.bat

# Linux/Mac: Start both backend and frontend (in my_ldpc_app/)
./start_app.sh
```

## Architecture Overview

### Frontend (Flutter)
- **Main App**: `lib/main.dart` - Entry point with Material Design dark theme
- **State Management**: Provider pattern with `AppProvider` (lib/providers/app_provider.dart) managing:
  - LDPC graph state (nodes, edges, selection)
  - Simulation results and parameters  
  - Encoding/decoding results and UI state
  - Text controllers for all input parameters
- **API Communication**: `lib/services/api_service.dart` using Dio HTTP client + WebSocket
  - Auto-detects backend URL based on platform (Web: 127.0.0.1:9999, Android: 10.0.2.2:9999)
  - Comprehensive error handling with localized messages
- **Key Dependencies**: dio, provider, web_socket_channel, fl_chart, uuid, collection
- **Key Components**:
  - `widgets/graph_canvas.dart` - Interactive LDPC graph editor with drag/drop nodes
  - `widgets/matrix_viewer.dart` - H-matrix visualization with zoom/pan
  - `widgets/ber_chart.dart` - Real-time BER performance curves using fl_chart
  - `widgets/control_panel.dart` - Simulation parameter controls
  - `widgets/resizable_panels.dart` - Responsive layout system
  - `screens/main_screen.dart` - Primary application interface
  - `pages/optimization_page.dart` - Genetic algorithm optimization interface

### Backend (Python FastAPI) 
- **API Server**: `main.py` - FastAPI with CORS, WebSocket support, runs on port 9999
- **Key Dependencies**: fastapi, uvicorn, numpy, scipy, pydantic, pyldpc, deap, psutil
- **Core Algorithms**:
  - `algorithms/ldpc_encoder.py` - LDPC encoding with systematic form, sparse matrix support
  - `algorithms/ldpc_decoder.py` - Multiple decoding algorithms (Min-Sum, Sum-Product/Belief Propagation)  
  - `algorithms/simulation_engine.py` - BER/FER performance simulation with configurable parameters
  - `algorithms/genetic_optimizer.py` - Genetic algorithm for code optimization using DEAP
- **Models**: 
  - `models/pydantic_models.py` - Request/response validation models
  - `models/ldpc_models.py` - Core LDPC code data structures
- **Utilities**: 
  - `utils/matrix_templates.py` - Pre-built LDPC matrix templates
  - `utils/error_handler.py` - Comprehensive error handling and logging
  - `utils/performance_utils.py` - Performance monitoring and metrics
- **Services**:
  - `services/task_manager.py` - Background task management
  - `services/websocket_manager.py` - WebSocket connection management

### API Endpoints Structure
- **Encoding**: `POST /api/v1/encode` - Generate H/G matrices from graph or direct input
- **Decoding**: `POST /api/v1/decode` - Decode with LLR, AWGN, or BSC channel models
- **Simulation**: 
  - `POST /api/simulate` - Full BER simulation across SNR range
  - `POST /api/quick-test` - Single SNR point rapid testing
  - `POST /api/simulate-from-graph` - Graph-based simulation
- **Templates**: 
  - `GET /api/matrix-templates` - Available LDPC matrix templates
  - `POST /api/generate-template` - Generate matrix from template
- **Monitoring**: `GET /api/performance-metrics` - System performance data

### Data Flow
1. Frontend creates LDPC graph (variable/check nodes + edges) via interactive canvas
2. Graph structure sent to backend → H-matrix generation → G-matrix computation
3. Encoding: Information bits → systematic encoding → codeword output
4. Channel simulation: AWGN/BSC noise addition with configurable parameters
5. Decoding: LLR computation → iterative decoding (Min-Sum/Sum-Product) → output bits
6. Statistics collection: BER/FER calculation across SNR points
7. Results streamed back via WebSocket for real-time visualization
8. Genetic optimizer evolves graph structure for performance optimization

### Key Features
- **Interactive Design**: Drag-drop graph creation with variable (V) and check (C) nodes
- **Multiple Templates**: Regular (3,6), (4,8) and irregular LDPC code templates
- **Real-time Visualization**: BER curves, H-matrix heatmaps, convergence monitoring
- **Multi-channel Support**: AWGN, BSC channel models with configurable parameters
- **Algorithm Options**: Min-Sum and Sum-Product decoding algorithms
- **Cross-platform**: Web, Windows desktop, Android, iOS support
- **Performance Monitoring**: Built-in profiling and metrics collection

### Testing Strategy
- **Unit Tests**: Core algorithms (encoder, decoder) with edge cases
- **Integration Tests**: API endpoints with real data flows
- **Performance Tests**: Large matrix operations and memory usage
- **Widget Tests**: Flutter UI components and user interactions

### Development Notes
- **Backend Port**: Configured to run on port 9999 (check main.py line 579)
- **Frontend Platform Detection**: Auto-configures API base URL based on runtime platform
- **State Management**: Provider pattern with comprehensive state tracking in AppProvider
- **Error Handling**: Enhanced error handling with user-friendly messages
- **WebSocket Support**: Real-time progress updates for long-running simulations
- **Matrix Operations**: Supports both sparse (scipy.sparse) and dense (numpy) matrices
- **API Documentation**: Auto-generated OpenAPI/Swagger docs at `/docs` endpoint