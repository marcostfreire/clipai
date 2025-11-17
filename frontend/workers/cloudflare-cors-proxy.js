const worker = {
    async fetch(request, env) {
        const targetBase = (env.RUNPOD_DIRECT_API_URL || 'https://qh3hpqrnck8ila-8000.direct.runpod.net/api').replace(/\/$/, '');
        const url = new URL(request.url);
        const proxiedPath = url.pathname.replace(/^\/api\/proxy/, '') || '/';
        const upstreamUrl = `${targetBase}${proxiedPath}${url.search}`;

        // Handle CORS preflight directly
        if (request.method === 'OPTIONS') {
            return new Response(null, {
                status: 204,
                headers: buildCorsHeaders(request.headers.get('Origin')),
            });
        }

        const init = {
            method: request.method,
            headers: new Headers(request.headers),
            redirect: 'manual',
        };

        if (!['GET', 'HEAD'].includes(request.method)) {
            init.body = request.body;
        }

        const upstreamResponse = await fetch(upstreamUrl, init);
        const responseHeaders = new Headers(upstreamResponse.headers);
        responseHeaders.set('Cache-Control', 'no-store');
        applyCors(responseHeaders, request.headers.get('Origin'));

        return new Response(upstreamResponse.body, {
            status: upstreamResponse.status,
            headers: responseHeaders,
        });
    },
};

export default worker;

function buildCorsHeaders(origin) {
    return {
        'Access-Control-Allow-Origin': origin || '*',
        'Access-Control-Allow-Methods': 'GET,POST,PUT,PATCH,DELETE,OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Requested-With, Accept',
        'Access-Control-Allow-Credentials': 'true',
        'Access-Control-Expose-Headers': '*',
        Vary: 'Origin',
    };
}

function applyCors(headers, origin) {
    const cors = buildCorsHeaders(origin);
    Object.entries(cors).forEach(([key, value]) => headers.set(key, value));
}
