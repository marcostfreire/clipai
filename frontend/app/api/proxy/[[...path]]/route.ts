import { NextRequest } from 'next/server';

export const runtime = 'edge';

const DEFAULT_TARGET = 'https://qh3hpqrnck8ila-8000.proxy.runpod.net/api';
const targetBase = (process.env.RUNPOD_DIRECT_API_URL || DEFAULT_TARGET).replace(/\/$/, '');
const ALLOWED_METHODS = 'GET,POST,PUT,PATCH,DELETE,OPTIONS';
const FALLBACK_ALLOWED_HEADERS = 'Content-Type, Authorization, X-Requested-With, Accept';

const buildTargetUrl = (segments: string[] | undefined, search: string) => {
    const encodedPath = segments?.length ? `/${segments.map((part) => encodeURIComponent(part)).join('/')}` : '';
    return `${targetBase}${encodedPath}${search}`;
};

const withCorsHeaders = (headers: Headers, origin?: string, request?: NextRequest) => {
    const corsHeaders: Record<string, string> = {
        'Access-Control-Allow-Origin': origin || '*',
        'Access-Control-Allow-Credentials': 'true',
        'Access-Control-Allow-Methods': ALLOWED_METHODS,
        'Access-Control-Expose-Headers': '*',
        'Vary': 'Origin',
    };

    const requestedHeaders = request?.headers.get('access-control-request-headers');
    corsHeaders['Access-Control-Allow-Headers'] = requestedHeaders || FALLBACK_ALLOWED_HEADERS;

    Object.entries(corsHeaders).forEach(([key, value]) => {
        headers.set(key, value);
    });

    return headers;
};

const proxyRequest = async (req: NextRequest, params: { path?: string[] }) => {
    if (!targetBase) {
        return new Response(
            JSON.stringify({ error: 'RUNPOD_DIRECT_API_URL is not configured' }),
            {
                status: 500,
                headers: withCorsHeaders(new Headers({ 'Content-Type': 'application/json' }), req.headers.get('origin') || '*', req),
            }
        );
    }

    const targetUrl = buildTargetUrl(params.path, req.nextUrl.search);
    const fetchHeaders = new Headers(req.headers);
    const forwardedHost = req.headers.get('host');

    fetchHeaders.delete('host');
    fetchHeaders.delete('content-length');
    fetchHeaders.delete('cf-ray');
    fetchHeaders.delete('cf-connecting-ip');
    fetchHeaders.delete('cf-ipcountry');

    if (forwardedHost) {
        fetchHeaders.set('x-forwarded-host', forwardedHost);
    }
    fetchHeaders.set('x-forwarded-proto', req.nextUrl.protocol.replace(':', ''));

    const fetchInit: RequestInit = {
        method: req.method,
        headers: fetchHeaders,
        redirect: 'manual',
    };

    if (!['GET', 'HEAD'].includes(req.method)) {
        fetchInit.body = req.body;
    }

    try {
        const upstreamResponse = await fetch(targetUrl, fetchInit);
        const responseHeaders = new Headers(upstreamResponse.headers);
        responseHeaders.delete('content-length');
        responseHeaders.set('Cache-Control', 'no-store');
        responseHeaders.set('CF-Cache-Status', 'DYNAMIC');
        withCorsHeaders(responseHeaders, req.headers.get('origin') || '*', req);

        return new Response(upstreamResponse.body, {
            status: upstreamResponse.status,
            headers: responseHeaders,
        });
    } catch (error) {
        const message = error instanceof Error ? error.message : 'Unknown error';
        const headers = withCorsHeaders(
            new Headers({ 'Content-Type': 'application/json', 'Cache-Control': 'no-store' }),
            req.headers.get('origin') || '*',
            req
        );

        return new Response(
            JSON.stringify({ error: 'Upstream request failed', detail: message, target: targetUrl }),
            { status: 502, headers }
        );
    }
};

export async function OPTIONS(req: NextRequest) {
    return new Response(null, {
        status: 204,
        headers: withCorsHeaders(new Headers(), req.headers.get('origin') || '*', req),
    });
}

export async function GET(req: NextRequest, context: { params: { path?: string[] } }) {
    return proxyRequest(req, context.params);
}

export async function POST(req: NextRequest, context: { params: { path?: string[] } }) {
    return proxyRequest(req, context.params);
}

export async function PUT(req: NextRequest, context: { params: { path?: string[] } }) {
    return proxyRequest(req, context.params);
}

export async function PATCH(req: NextRequest, context: { params: { path?: string[] } }) {
    return proxyRequest(req, context.params);
}

export async function DELETE(req: NextRequest, context: { params: { path?: string[] } }) {
    return proxyRequest(req, context.params);
}
