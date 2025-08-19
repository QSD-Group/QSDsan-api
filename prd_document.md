# Product Requirements Document (PRD)
# Waste-to-Energy Processing API

**Version:** 2.0.0  
**Status:** Development  
**Last Updated:** August 2025  

---

## 📋 **Project Overview**

### **Problem Statement**
The current Flask-based Waste-to-Energy Processing API suffers from:
- **Performance Issues**: Slow response times due to complex scientific calculations
- **Reliability Issues**: HTL endpoints work, but combustion and fermentation endpoints fail in production
- **Technical Debt**: Outdated dependency management, poor error handling, and lack of caching
- **Scalability Concerns**: Single-threaded Flask application with CSV-based data storage

### **Solution**
Modernize the API with FastAPI, improved dependency management, local caching, and optimized data access patterns while maintaining calculation accuracy and expanding functionality.

### **Success Metrics**
- 🎯 **Performance**: <500ms average response time (vs current unknown/timeout)
- 🎯 **Reliability**: 99.9% uptime, all endpoints functional
- 🎯 **Accuracy**: Maintain 100% calculation accuracy vs existing validated results
- 🎯 **Developer Experience**: Hot reload, auto-generated docs, type safety

---

## 🏗️ **System Architecture**

### **High-Level Architecture**
```
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Application                      │
├─────────────────┬─────────────────┬─────────────────────────┤
│   HTL Service   │ Combustion Svc  │  Fermentation Service   │
│   (Working)     │   (Needs Fix)   │    (Needs Fix)         │
└─────────────────┴─────────────────┴─────────────────────────┘
                           │
                ┌─────────────────────┐
                │    Data Layer       │
                ├─────────────────────┤
                │  CSV Files (Now)    │
                │  SQLite (Future)    │
                │  Redis Cache (Opt)  │
                └─────────────────────┘
```

### **Technology Stack**
- **API Framework**: FastAPI (replacing Flask)
- **Dependency Management**: uv (10-100x faster than pip)
- **Scientific Computing**: biosteam, exposan, biorefineries, pandas
- **Data Storage**: CSV files → SQLite (phase 2)
- **Caching**: In-memory → Redis (optional)
- **Container**: Docker with multi-stage builds
- **Documentation**: Auto-generated OpenAPI/Swagger docs

---

## 🎯 **Core Features**

### **1. HTL (Hydrothermal Liquefaction) Processing**
**Status**: ✅ Working, needs optimization  
**Purpose**: Convert sludge waste to diesel fuel

#### **Endpoints**:
- `GET /api/v1/htl/calc` - Calculate diesel production from sludge mass
- `GET /api/v1/htl/county` - Get HTL potential for specific NJ county

#### **Input Parameters**:
- `sludge`: Mass of sludge (float)
- `unit`: Unit of measurement (`kghr`, `tons`, `tonnes`, `mgd`, `m3d`)
- `county_name`: New Jersey county name (string)

#### **Output**:
- `sludge_kg_hr`: Normalized mass in kg/hr
- `price_per_gallon`: Minimum diesel selling price ($/gallon)
- `gwp_lb_co2_per_gallon`: Global warming potential (lb CO2e/gallon)

### **2. Combustion Processing**
**Status**: ❌ Broken, needs fixing  
**Purpose**: Convert various waste types to electricity

#### **Endpoints**:
- `GET /api/v1/combustion/calc` - Calculate electricity generation from waste
- `GET /api/v1/combustion/county` - Get combustion potential for specific county

#### **Input Parameters**:
- `mass`: Mass of feedstock (float)
- `unit`: Unit of measurement (`kghr`, `tons`, `tonnes`, `mgd`, `m3d`)
- `waste_type`: Type of waste (`sludge`, `food`, `fog`, `green`, `manure`)
- `county_name`: New Jersey county name (string)

#### **Output**:
- `mass_kg_hr`: Normalized mass in kg/hr
- `waste_type`: Waste type used
- `annual_electricity_mwh`: Annual electricity production (MWh)
- `avoided_emissions_mmt`: Avoided emissions (million metric tonnes)
- `emissions_percent`: Fraction of total NJ emissions avoided

### **3. Fermentation Processing**
**Status**: ❌ Broken, needs fixing  
**Purpose**: Convert biomass to ethanol

#### **Endpoints**:
- `GET /api/v1/fermentation/calc` - Calculate ethanol production from biomass
- `GET /api/v1/fermentation/county` - Get fermentation potential for specific county

#### **Input Parameters**:
- `mass`: Mass of feedstock (float)
- `unit`: Unit of measurement (`kghr`, `tons`, `tonnes`)
- `county_name`: New Jersey county name (string)

#### **Output**:
- `mass_kg_hr`: Normalized mass in kg/hr
- `annual_ethanol_mmgal`: Annual ethanol production (MM gallons/year)
- `price_per_gallon`: Ethanol price ($/gallon)
- `gwp_lb_co2_per_gallon`: Greenhouse gas emissions (lb CO2e/gallon)

---

## 📊 **Data Architecture**

### **Current Data Sources**
Located in `app/data/` directory:

1. **Combustion Data** (`combustion/combustion_data.csv`)
   - 21 NJ counties with waste quantities by type
   - Columns: County, Sludge (MGD), Food (tons), Food (dry tons), Fog (tons), Fog (dry tons), Green (dry tons), Manure (lbs)

2. **Fermentation Data** (`fermentation/fermentation_data.csv`)
   - Lignocellulose availability by county
   - Columns: County, Lignocellulose (dry tons), Kilogram, Kilogram/hr, Annual Ethanol (gal/yr), Price ($/gal), GWP (kg CO2e/gal)

3. **HTL Data** (`htl/htl_data.csv`)
   - Sludge disposal methods by county
   - Columns: County, Incineration, Class A/B Beneficial Use, Out-of-State options, County Total (Dry Metric Tonnes/Year)

### **Data Processing Strategy**
- **Phase 1**: Continue using CSV files with pandas for data loading
- **Phase 2**: Migrate to SQLite for better performance and ACID compliance
- **Phase 3**: Add caching layer for expensive calculations

---

## 🔧 **Technical Implementation**

### **Project Structure**
```
waste-energy-api/
├── README.md
├── PRD.md                    # This document
├── Dockerfile                # Multi-stage Docker build
├── docker-compose.yml        # Local development
├── pyproject.toml           # uv dependency management
├── uv.lock                  # Locked dependencies
├── .env.example             # Environment variables template
├── .github/
│   └── workflows/
│       └── ci.yml           # GitHub Actions CI/CD
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration management
│   ├── models/              # Pydantic response models
│   │   ├── __init__.py
│   │   ├── htl.py
│   │   ├── combustion.py
│   │   └── fermentation.py
│   ├── services/            # Business logic (existing)
│   │   ├── __init__.py
│   │   ├── htl_service.py
│   │   ├── combustion_service.py
│   │   └── fermentation_service.py
│   ├── routers/             # FastAPI route handlers
│   │   ├── __init__.py
│   │   ├── htl.py
│   │   ├── combustion.py
│   │   ├── fermentation.py
│   │   └── admin.py
│   ├── data/                # CSV data files (current)
│   │   ├── combustion/
│   │   │   └── combustion_data.csv
│   │   ├── fermentation/
│   │   │   └── fermentation_data.csv
│   │   └── htl/
│   │       └── htl_data.csv
│   └── utils/               # Utility functions
│       ├── __init__.py
│       ├── cache.py         # Caching utilities
│       ├── validation.py    # Input validation
│       └── errors.py        # Custom exceptions
├── database/                # Future SQLite integration
│   ├── schema.sql           # Database schema
│   ├── migrations/          # Database migrations
│   └── seed_data.py         # CSV to SQLite migration
├── tests/
│   ├── __init__.py
│   ├── test_htl.py
│   ├── test_combustion.py
│   ├── test_fermentation.py
│   └── test_integration.py
└── scripts/
    ├── migrate_data.py      # Data migration utilities
    └── precompute.py        # Pre-computation scripts
```

### **FastAPI Implementation Highlights**

#### **1. Async/Await Support**
```python
@app.get("/api/v1/htl/calc")
async def htl_calculation(
    sludge: float = Query(..., gt=0, description="Sludge mass"),
    unit: Literal["kghr", "tons", "tonnes", "mgd", "m3d"] = "kghr"
):
    # Async processing for better performance
    result = await calculate_htl_async(sludge, unit)
    return HTLResponse(**result)
```

#### **2. Automatic Input Validation**
```python
class HTLRequest(BaseModel):
    sludge: float = Field(gt=0, description="Sludge mass must be positive")
    unit: Literal["kghr", "tons", "tonnes", "mgd", "m3d"] = "kghr"
    
    @validator('sludge')
    def validate_sludge_range(cls, v):
        if v > 1e9:  # Reasonable upper limit
            raise ValueError('Sludge mass too large')
        return v
```

#### **3. Comprehensive Error Handling**
```python
class CalculationError(HTTPException):
    def __init__(self, detail: str, error_code: str = None):
        super().__init__(status_code=422, detail=detail)
        self.error_code = error_code

@app.exception_handler(CalculationError)
async def calculation_error_handler(request: Request, exc: CalculationError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "error_code": exc.error_code}
    )
```

### **Dependency Management with uv**

#### **pyproject.toml Configuration**
```toml
[project]
name = "waste-energy-api"
version = "2.0.0"
description = "High-performance API for waste-to-energy calculations"
requires-python = ">=3.10"
dependencies = [
    "fastapi>=0.104.0",
    "uvicorn[standard]>=0.24.0",
    "pandas>=2.2.3",
    "numpy>=1.26.4",
    "biosteam",
    "biorefineries",
    "chaospy==4.3.17",
    "exposan @ git+https://github.com/QSD-Group/EXPOsan.git@93d4173",
]

[project.optional-dependencies]
dev = ["pytest>=7.0.0", "black>=23.0.0", "ruff>=0.1.0"]
cache = ["redis>=5.0.0"]
database = ["aiosqlite>=0.19.0"]
```

### **Docker Optimization**

#### **Multi-Stage Dockerfile**
```dockerfile
# Builder stage - compile dependencies
FROM python:3.10-slim as builder
RUN apt-get update && apt-get install -y gcc g++ gfortran git
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-cache

# Runtime stage - minimal footprint
FROM python:3.10-slim as runtime
RUN apt-get update && apt-get install -y libopenblas0 liblapack3
COPY --from=builder /app/.venv /app/.venv
WORKDIR /app
COPY . .
ENV PATH="/app/.venv/bin:$PATH"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "5000"]
```

---

## 🧪 **Testing Strategy**

### **Test Categories**

1. **Unit Tests** - Individual function testing
   - Service layer calculations
   - Data transformation functions
   - Input validation logic

2. **Integration Tests** - End-to-end API testing
   - Full request/response cycles
   - Error handling scenarios
   - Data consistency checks

3. **Performance Tests** - Response time verification
   - Load testing with multiple concurrent requests
   - Memory usage monitoring
   - Calculation accuracy under load

### **Test Data**
- Use actual county data for integration tests
- Mock expensive calculations for unit tests
- Validate against known good results from current system

---

## 🔄 **Development Workflow**

### **Local Development Setup**
```bash
# 1. Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Clone and setup
git clone <repository>
cd waste-energy-api
uv sync

# 3. Start development server
uv run uvicorn app.main:app --reload --port 5000

# 4. Run tests
uv run pytest

# 5. Docker development
docker-compose up -d
```

### **Development Standards**
- **Code Formatting**: Black + Ruff
- **Type Checking**: mypy with strict mode
- **Testing**: pytest with coverage >90%
- **Documentation**: Docstrings for all public functions
- **Git Workflow**: Feature branches with PR reviews

---

## 📈 **Performance Requirements**

### **Response Time Targets**
- **HTL Calculations**: <200ms (currently working)
- **Combustion Calculations**: <500ms (needs fixing)
- **Fermentation Calculations**: <500ms (needs fixing)
- **County Data Queries**: <100ms
- **Health Check**: <50ms

### **Throughput Targets**
- **Concurrent Requests**: Support 50+ simultaneous calculations
- **Peak Load**: 1000 requests/minute
- **Cache Hit Rate**: >80% for repeated county queries

### **Resource Constraints**
- **Memory Usage**: <512MB for basic calculations
- **CPU Usage**: <50% during normal operation
- **Docker Image Size**: <500MB

---

## 🚀 **Implementation Phases**

### **Phase 1: Foundation (Week 1)**
**Goal**: Get all endpoints working reliably

- [ ] Set up uv dependency management
- [ ] Fix requirements.txt and Docker build issues
- [ ] Migrate from Flask to FastAPI
- [ ] Debug and fix combustion/fermentation endpoints
- [ ] Add comprehensive error handling and logging
- [ ] Create health check endpoints

**Deliverables**:
- Working FastAPI application with all endpoints functional
- Optimized Docker container with fast builds
- Auto-generated API documentation
- Basic integration tests

### **Phase 2: Optimization (Week 2-3)**
**Goal**: Improve performance and developer experience

- [ ] Implement in-memory caching for calculations
- [ ] Add input validation and sanitization
- [ ] Create comprehensive test suite
- [ ] Set up CI/CD pipeline
- [ ] Performance optimization and monitoring
- [ ] Add admin endpoints for debugging

**Deliverables**:
- <500ms response times for all endpoints
- 90%+ test coverage
- Automated testing and deployment
- Performance monitoring dashboard

### **Phase 3: Enhancement (Week 4+)**
**Goal**: Prepare for future scaling

- [ ] Design SQLite migration strategy
- [ ] Implement data export/import utilities
- [ ] Add API versioning support
- [ ] Create comprehensive documentation
- [ ] Implement rate limiting and security features
- [ ] Plan cloud deployment architecture

**Deliverables**:
- SQLite integration ready for deployment
- Production-ready security features
- Comprehensive API documentation
- Cloud deployment plan (for future phases)

---

## 🎯 **Success Criteria**

### **Week 1 Goals (Minimum Viable Product)**
- ✅ All three process types (HTL, Combustion, Fermentation) working
- ✅ All 21 NJ counties returning valid data
- ✅ FastAPI with auto-generated documentation
- ✅ Docker container builds successfully and runs
- ✅ Basic error handling and logging
- ✅ Response times <1 second for all endpoints

### **Week 2-3 Goals (Optimized Product)**
- ✅ Response times <500ms average
- ✅ 90%+ test coverage
- ✅ CI/CD pipeline operational
- ✅ In-memory caching implemented
- ✅ Comprehensive input validation
- ✅ Performance monitoring

### **Long-term Goals (Scalable Product)**
- ✅ SQLite integration for better data management
- ✅ Redis caching for high performance
- ✅ API versioning and backward compatibility
- ✅ Security features (rate limiting, API keys)
- ✅ Cloud deployment ready

---

## 🔧 **Configuration Management**

### **Environment Variables**
```bash
# Application
ENVIRONMENT=development|staging|production
LOG_LEVEL=DEBUG|INFO|WARNING|ERROR
API_VERSION=v1

# Performance
CACHE_TTL=3600
MAX_CALCULATION_TIME=30
WORKER_PROCESSES=2

# Data
DATA_PATH=./app/data
SQLITE_PATH=./database/waste_energy.db  # Future

# Optional Features
ENABLE_REDIS_CACHE=false
REDIS_URL=redis://localhost:6379
ENABLE_RATE_LIMITING=false
```

### **Feature Flags**
- `USE_SQLITE`: Switch from CSV to SQLite storage
- `ENABLE_CACHING`: Toggle caching layer
- `STRICT_VALIDATION`: Enhanced input validation
- `PERFORMANCE_MONITORING`: Detailed metrics collection

---

## 📝 **API Documentation**

### **Auto-Generated Documentation**
FastAPI automatically generates:
- **OpenAPI/Swagger UI**: Interactive API documentation at `/docs`
- **ReDoc**: Alternative documentation at `/redoc`
- **OpenAPI Schema**: Machine-readable schema at `/openapi.json`

### **Custom Documentation**
- **README.md**: Setup and usage instructions
- **API_GUIDE.md**: Detailed endpoint documentation with examples
- **DEPLOYMENT.md**: Deployment and configuration guide
- **TROUBLESHOOTING.md**: Common issues and solutions

---

## 🎉 **Project Benefits**

### **Immediate Benefits (Week 1)**
- **Reliability**: All endpoints working instead of 2/3
- **Performance**: Faster response times with async processing
- **Developer Experience**: Auto-generated docs, type safety, hot reload
- **Maintainability**: Modern Python practices, better error handling

### **Medium-term Benefits (Month 1)**
- **Scalability**: Async architecture supports higher concurrent load
- **Efficiency**: Caching reduces repeated expensive calculations
- **Quality**: Comprehensive testing ensures reliability
- **Security**: Input validation and rate limiting

### **Long-term Benefits (Quarter 1)**
- **Data Management**: SQLite provides better data integrity and query performance
- **Extensibility**: Clean architecture supports new process types
- **Monitoring**: Performance insights and debugging capabilities
- **Cloud Ready**: Architecture prepared for cloud deployment when needed

---

*This PRD serves as the single source of truth for the Waste-to-Energy API modernization project. All development decisions should align with the goals and requirements outlined in this document.*