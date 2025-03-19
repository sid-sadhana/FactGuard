const pg = require('pg')
import { NextRequest,NextResponse } from 'next/server'
const argon2 = require('argon2');

const { Client } = pg

export async function POST(req: NextRequest, res: NextResponse) {
    const body = await req.json()
    console.log(body)
    const client = new Client({
        user: 'postgres',
        password: 'sid123',
        host: 'localhost',
        database: 'test'
    })
    return NextResponse.json({"message":"success"})
}
