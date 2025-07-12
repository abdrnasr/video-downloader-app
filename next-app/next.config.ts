import type { NextConfig } from "next"; 


/**
 * Tries to parse a URL and returns an object with host and port.
 * If the port is not specified, it defaults to "default".
 * If the URL is invalid, it returns null and logs an error.
 * @param url The URL to parse.
 * @returns An object with host and port, or null if the URL is invalid.
 */
const parseURL = (url: string) => {
    try {
        const parsed = new URL(url);
        const protocol = parsed.protocol.replace(":", ""); // Remove trailing colon from protocol

        return { protocol, host: parsed.hostname, port:parsed.port };
    } catch {
        return null; // Invalid URL
    }
};


// Extracts the backend address from the enviornment variable and try to parse it.
const defaultURL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
const parsedURL = parseURL(defaultURL);

// Extract the appropriate address values and utilize defaults if necessary
let selectedProtocol: "http" | "https" | undefined = undefined;
if (parsedURL?.protocol === "http:") {
    selectedProtocol = "http";
} else if (parsedURL?.protocol === "https:") {
    selectedProtocol = "https";
}
const backendAddress= parsedURL?.host || '127.0.0.1';
const backendPort = (!parsedURL?.port || parsedURL.port === "default") ? "8000" : parsedURL.port;

// This is to allow the Image component provided by Next.js to fetch images from the backend.
// Without specifying the correct protocol, hostname, and port, Images will not be fetched.
const nextConfig: NextConfig = {
    images:{
        remotePatterns:[
        {
            protocol: selectedProtocol,
            hostname: backendAddress,
            port:backendPort,
            pathname:'/thumbnails/**'}
        ]
    }
};

export default nextConfig;
