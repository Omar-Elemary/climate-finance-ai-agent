# Climate Finance AI Agent - Frontend

This is the React frontend for the Climate Finance AI Agent application, featuring an engaging and attractive user interface designed to facilitate multi-agent discussions on climate finance topics.

## Features

- Beautiful Topic Selection: Engaging interface with gradient backgrounds, animated elements, and intuitive controls
- Interactive Discussion View: Visually appealing message cards with agent avatars, timestamps, and round indicators
- Comprehensive Analytics Dashboard: Rich data visualizations including opinion trajectories, agreement levels, influence scores, and interaction graphs
- Responsive design with Tailwind CSS
- TypeScript for type safety
- Dockerized for easy deployment

## Features

- Topic selection interface
- Multi-agent discussion view
- Analytics dashboard showing opinion trajectory, agreement, influence, and interaction graph
- Responsive design with Tailwind CSS
- TypeScript for type safety
- Dockerized for easy deployment

## Technology Stack

- React 18 with TypeScript
- Vite for fast development builds
- React Router v6 for client-side routing
- Axios for HTTP requests
- Recharts for data visualization
- Tailwind CSS for styling

## Getting Started

### Prerequisites

- Node.js (v16 or higher)
- npm or yarn

### Installation

1. Clone the repository
2. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```
3. Install dependencies:
   ```bash
   npm install
   ```

### Development

To start the development server:

```bash
npm run dev
```

The frontend will be available at `http://localhost:5173` and will proxy API requests to `http://localhost:8000/api`.

### Building for Production

To create a production build:

```bash
npm run build
```

The built assets will be in the `dist` directory.

### Docker

To build and run the Docker container:

```bash
# Build the image
docker build -t climate-finance-frontend .

# Run the container
docker run -p 80:80 climate-finance-frontend
```

The application will be available at `http://localhost`.

## Environment Variables

Create a `.env` file in the frontend directory based on `.env.example`:

```
VITE_API_URL=http://localhost:8000/api
```

## Project Structure

```
frontend/
├── src/
│   ├── api/          # API service functions
│   ├── components/   # Reusable UI components
│   ├── contexts/     # React context providers
│   ├── pages/        # Page components (routes)
│   ├── App.tsx       # Main app component
│   ├── main.tsx      # Entry point
│   └── index.css     # Global styles
├── public/
├── Dockerfile
├── vite.config.ts
├── tailwind.config.js
├── postcss.config.js
└── tsconfig.json
```

## API Integration

The frontend communicates with the backend API at `/api` (proxied during development). Key endpoints:

- `GET /api/topics` - Get available topics
- `POST /api/discussions` - Create a new discussion
- `GET /api/discussions/{id}` - Get discussion data
- `GET /api/discussions/{id}/analytics` - Get analytics data

## Design Decisions

1. **State Management**: Used React Context API for simplicity given the app's scale
2. **Styling**: Enhanced Tailwind CSS with custom gradients, animations, and responsive design principles
3. **Data Visualization**: Recharts for standard charts with custom animations and gradients, custom implementation for interaction graph with advanced visual effects
4. **Routing**: React Router v6 for client-side navigation with smooth transitions
5. **Error Handling**: User-friendly error boundaries with helpful recovery suggestions and engaging empty states
6. **Loading States**: Engaging skeletons, spinners, and placeholder content with informative messaging for better UX during asynchronous operations
7. **Visual Design**: Applied elevation, depth, and motion principles to create a modern, engaging interface that maintains professionalism while being visually appealing
8. **Accessibility**: Ensured proper color contrast, focus management, and semantic HTML structure

## Browser Support

Supports modern browsers that support ES2020 features:
- Chrome 64+
- Firefox 60+
- Safari 12.1+
- Edge 79+