// API Proxy - Reports endpoint
const BACKEND_URL = process.env.BACKEND_API_URL || 'http://localhost:8000';

export async function GET(request: Request) {
    try {
        const url = new URL(request.url);
        const endpoint = url.pathname.replace('/api/proxy/reports/', '/reports/');

        const response = await fetch(`${BACKEND_URL}${endpoint}`);

        // Handle PDF downloads
        if (response.headers.get('content-type')?.includes('application/pdf')) {
            const blob = await response.blob();
            return new Response(blob, {
                status: response.status,
                headers: {
                    'Content-Type': 'application/pdf',
                    'Content-Disposition': response.headers.get('Content-Disposition') || 'attachment',
                },
            });
        }

        const data = await response.json();
        return Response.json(data, { status: response.status });
    } catch (error) {
        console.error('Reports proxy error:', error);
        return Response.json(
            { detail: 'Failed to fetch report' },
            { status: 500 }
        );
    }
}
