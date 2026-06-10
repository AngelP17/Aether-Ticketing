import { NextResponse } from "next/server";

export const dynamic = "force-static";

export function GET() {
  return NextResponse.json({
    status: "healthy",
    service: "aether-web",
  });
}

export function HEAD() {
  return new Response(null, { status: 200 });
}
