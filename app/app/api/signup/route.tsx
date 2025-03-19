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
    const hash = await argon2.hash(body.password);
    try {
        await client.connect()
        const res = await client.query(`SELECT * FROM factguard WHERE email = '${body.email}';`)
        const res2=await client.query(`SELECT MAX(user_id) FROM factguard;`)
        var id =0
        if(res2.rows[0].max===null){
            id=1
        }
        else{
            id=res2.rows[0].max+1
        }
        if(res.rows.length===0){
            const res = await client.query(`INSERT INTO factguard(user_id,email,hash) VALUES ('${id}','${body.email}','${hash}');`)
        }
        await client.end()
        return NextResponse.json({"message":"success"})
    } catch (error) {
        console.error('Error executing query:', error)
    }
}
