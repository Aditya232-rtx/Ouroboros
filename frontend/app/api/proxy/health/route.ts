// API Proxy - Health check endpoint
const BACKEND_URL = process.env.BACKEND_API_URL || 'http://localhost:8000';

export async function GET() {
    try {
        const response = await fetch(`${BACKEND_URL}/health`);
        const data = await response.json();
        return Response.json(data, { status: response.status });
    } catch (error) {
        console.error('Health proxy error:', error);
        return Response.json(
            { status: 'error', message: 'Backend unreachable' },
            { status: 503 }
        );
    }
}
