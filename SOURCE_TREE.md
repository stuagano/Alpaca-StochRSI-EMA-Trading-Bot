# Source Tree Documentation

## Project Structure Overview
This document describes the complete source code organization and the purpose of each directory and important file.

## Directory Structure
```
project-root/
├── docs/                           # Project documentation
│   ├── architecture/               # Architecture documentation
│   │   ├── system-overview.md      # High-level system design
│   │   ├── component-design.md     # Detailed component specifications
│   │   └── decisions.md           # Architectural decision log
│   ├── api/                       # API documentation
│   └── guides/                    # User and developer guides
├── src/                           # Source code
│   ├── components/                # Reusable UI components
│   ├── services/                  # Business logic and services
│   ├── utils/                     # Utility functions and helpers
│   ├── types/                     # TypeScript type definitions
│   └── tests/                     # Test files
├── tasks/                         # Project management
│   ├── epic-*.md                  # Epic documentation
│   └── story-*.md                 # User story documentation
├── config/                        # Configuration files
├── scripts/                       # Build and deployment scripts
├── public/                        # Static assets
└── README.md                      # Project overview and setup
```

## Key Directories and Files

### `/docs` - Documentation
**Purpose:** Contains all project documentation including architecture, API specs, and guides.

- **`architecture/`** - System design documents and architectural decisions
- **`api/`** - API documentation, OpenAPI specs, and integration guides  
- **`guides/`** - User manuals, developer setup guides, and tutorials

### `/src` - Source Code
**Purpose:** All application source code organized by functionality.

- **`components/`** - Reusable UI components with clear interfaces
- **`services/`** - Business logic, API clients, and data management
- **`utils/`** - Pure utility functions used across the application
- **`types/`** - TypeScript interfaces and type definitions
- **`tests/`** - Unit tests, integration tests, and test utilities

### `/tasks` - Project Management  
**Purpose:** Agile project management documents following BMAD methodology.

- **Epic files (`epic-*.md`)** - High-level feature descriptions with business value
- **Story files (`story-*.md`)** - Detailed user stories with acceptance criteria

### `/config` - Configuration
**Purpose:** Environment-specific configuration and settings.

- Database connection settings
- API endpoint configurations  
- Feature flags and environment variables

### `/scripts` - Automation
**Purpose:** Build, test, and deployment automation scripts.

- Build scripts for different environments
- Database migration scripts
- Deployment automation

## File Naming Conventions

### Documentation Files
- Use kebab-case: `system-overview.md`
- Include version in filename if needed: `api-spec-v2.md`
- Use descriptive names: `user-authentication-flow.md`

### Source Code Files  
- Components: PascalCase `UserProfile.tsx`
- Services: camelCase `userService.ts`
- Utilities: camelCase `dateUtils.ts`
- Types: PascalCase `UserTypes.ts`

### Task Files
- Epics: `epic-user-management.md`
- Stories: `story-user-login.md`
- Use descriptive names that reflect the feature

## Code Organization Principles

### Separation of Concerns
- UI components only handle presentation
- Services handle business logic and data
- Utilities provide pure functions
- Types define clear interfaces

### Dependency Direction
- Components depend on services
- Services depend on utilities
- No circular dependencies allowed
- External dependencies isolated in service layer

### Testing Strategy
- Unit tests co-located with source files
- Integration tests in dedicated test directories
- End-to-end tests in separate test suite
- Mock external dependencies

## Navigation Guide

### For New Developers
1. Start with `README.md` for project overview
2. Review `docs/architecture/system-overview.md` for system understanding
3. Check `tasks/` directory for current development priorities
4. Explore `src/` directory for code organization

### For Project Managers
1. Review `tasks/` directory for epic and story status
2. Check `docs/` for current documentation status
3. Use `PRD.md` for requirements tracking

### For Architects
1. Focus on `docs/architecture/` directory
2. Review `src/` organization for implementation alignment
3. Check `config/` for system configuration

---
*Last Updated: 2025-08-21*  
*Maintained by: Development Team*
