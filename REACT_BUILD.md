# Building React Components for AlphaTest

## Setup

1. **Install Node.js dependencies:**
```bash
cd /home/user/alphatest
npm install
```

2. **Build React components:**
```bash
npm run build
```

This will compile the TypeScript/React code and generate `static/dist/collaboration-bundle.js`.

## Development

To watch for changes and rebuild automatically:
```bash
npm run dev
```

## File Structure

```
alphatest/
├── package.json                          # NPM dependencies
├── webpack.config.js                     # Webpack configuration
├── tsconfig.json                         # TypeScript configuration
├── static/
│   ├── js/
│   │   ├── collaboration.tsx             # React entry point
│   │   ├── collaboration.css             # Global styles
│   │   └── components/
│   │       ├── CollaborationDashboard.tsx
│   │       ├── CollaboratorBar.tsx
│   │       ├── IssueBuckets.tsx
│   │       ├── IssueCard.tsx
│   │       ├── IssueRegister.tsx
│   │       ├── InviteModal.tsx
│   │       └── types.ts
│   └── dist/
│       └── collaboration-bundle.js       # Generated bundle
└── templates/
    └── collaboration.html                # Flask template
```

## Accessing the Collaboration Dashboard

Once built, access the dashboard at:
```
http://localhost:5000/project/{project_id}/collaboration
```

## API Endpoints

The React app consumes these Flask API endpoints:

- `GET /api/project/{project_id}/collaborators` - Get project collaborators
- `GET /api/project/{project_id}/issues` - Get project issues
- `POST /api/project/{project_id}/invite` - Invite collaborator
- `POST /api/project/{project_id}/export-issues` - Export issues to PDF
- `POST /api/project/{project_id}/save` - Save project state

## Production Build

For production, the build process is:
1. `npm run build` - Generates optimized bundle
2. Deploy to Cloud Run with the generated bundle

The bundle is already configured in webpack to output to `static/dist/`.
