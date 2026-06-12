// Proxy for status endpoint
const API_BASE_URL = process.env.BACKEND_API_URL || 'http://localhost:8000';

export async function GET(
    request: Request,
    { params }: { params: Promise<{ scanId: string }> }
) {
    try {
        const { scanId } = await params;
        const response = await fetch(`${API_BASE_URL}/status/${scanId}`, {
            headers: {
                cookie: request.headers.get("cookie") || "",
            },
        });

        if (!response.ok) {
            return Response.json(
                { error: 'Status not found' },
                { status: response.status }
            );
        }

        const data = await response.json();
        return Response.json(data);
    } catch (error) {
        console.error('Proxy error:', error);
        return Response.json(
            { error: 'Failed to fetch status' },
            { status: 500 }
        );
    }
}
