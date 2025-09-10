# GARNET - Sistema de Gestão Industrial

## Overview

GARNET is a comprehensive industrial management system built with Python and Streamlit for managing manufacturing operations. The system handles suppliers, raw materials, products, formulations, inventory, production orders, purchasing, quality control, and financial operations. It features a role-based authentication system with different access levels (manager, operator, viewer) and provides real-time KPIs, reporting, and cost analysis capabilities.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
- **Framework**: Streamlit multipage application with pages organized in a `pages/` directory
- **UI Pattern**: Tab-based interface within each page for logical grouping of functionality
- **Design System**: Professional, minimalist corporate design with clean typography and corporate blue color scheme (#2E4A6B)
- **Layout**: Consistent page headers, standardized forms, and professional KPI cards without excessive icons or emojis
- **Caching Strategy**: Uses `@st.cache_resource` for database connections and `@st.cache_data` for report generation with TTL
- **State Management**: Streamlit session state for user authentication and temporary data storage

### Backend Architecture
- **Database ORM**: SQLModel (built on SQLAlchemy) for database operations and Pydantic for data validation
- **Authentication**: Custom authentication system using passlib with bcrypt hashing
- **Authorization**: Role-based access control (RBAC) with three default roles: manager, operator, viewer
- **Business Logic**: Separated into service modules:
  - `services/business.py` - Core business calculations (costs, MRP, FEFO)
  - `services/reports.py` - Report generation and KPI calculations
  - `services/io_import.py` - Data import functionality
  - `services/io_export.py` - Data export functionality

### Data Architecture
- **Database Engine**: Flexible database support with SQLite for development and PostgreSQL for production
- **Connection Management**: Environment variable-based configuration with fallback to SQLite
- **Models**: Comprehensive data models covering:
  - User management and authentication
  - Supplier and vendor information
  - Raw materials and finished products
  - Formulations and bill of materials
  - Inventory and stock lot tracking
  - Production and purchase orders
  - Quality control and testing
  - Financial transactions

### Core Business Features
- **Inventory Management**: FEFO (First Expired, First Out) picking logic and stock valuation
- **Production Planning**: MRP (Material Requirements Planning) calculations
- **Cost Analysis**: Dynamic cost calculations for formulations and products
- **Quality Control**: Lot tracking and quality test management
- **Financial Management**: Accounts payable and cash flow tracking

## External Dependencies

### Core Framework Dependencies
- **Streamlit**: Web application framework for the user interface
- **SQLModel**: Database ORM combining SQLAlchemy and Pydantic
- **SQLAlchemy**: Core database toolkit and ORM
- **Pydantic**: Data validation and settings management

### Authentication & Security
- **passlib[bcrypt]**: Password hashing and verification

### Data Processing & Visualization
- **pandas**: Data manipulation and analysis
- **numpy**: Numerical computing support
- **plotly**: Interactive charts and data visualization

### Database Connectors
- **psycopg2-binary**: PostgreSQL adapter for production environments
- **SQLite**: Built-in Python database for development (no additional dependency)

### Import/Export Capabilities
- **openpyxl**: Excel file reading and writing
- **reportlab**: PDF generation (optional)

### Configuration Management
- **python-dotenv**: Environment variable management

### Database Configuration
- Development: SQLite database stored in `data/app.db`
- Production: PostgreSQL via `DATABASE_URL` environment variable
- Automatic fallback mechanism from PostgreSQL to SQLite for development

The system is designed to be deployed on cloud platforms with minimal configuration, requiring only the `DATABASE_URL` environment variable for production PostgreSQL connections.