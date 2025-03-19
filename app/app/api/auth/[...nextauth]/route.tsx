import NextAuth from "next-auth"
import GoogleProvider from "next-auth/providers/google"

const handler = NextAuth({
  providers:[
    GoogleProvider({
        clientId: process.env.GOOGLE_CLIENT_ID || '', // Provide a default empty string
        clientSecret: process.env.GOOGLE_CLIENT_SECRET || '', // Provide a default empty string
    })
  ]
})

export { handler as GET, handler as POST }
