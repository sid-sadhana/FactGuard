"use client"
import React,{useState} from 'react';
import { signIn, signOut, useSession } from 'next-auth/react'
import {useRouter} from 'next/navigation'
import axios from 'axios'
const SignInPage = () => {
    const session = useSession();
    console.log(session)
    const router=useRouter();
    const[email, set_email] = useState("");
    const[password, set_password] = useState("");
    const send_data=async()=>{
            const response = await axios.post("/api/signin",{email:email,password:password})
            console.log(response.data)
    }
    if(session.status==="authenticated"){
        router.push("/")
    }
    if (session.status === "loading") {
        return (
        <div className="flex justify-center mt-56">
        <img src="https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExY2N4eWw2c3F0dnRkcDJqMDNyNWdsanIxeHh4dmdudHRlZ2Z0dzB4YyZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9cw/zFwqvI1atpDkLPhBgY/giphy.gif"></img>
        </div>
      )
      }
    return (
        <div className="h-screen bg-[#181b2b]"> 
        <div className="flex flex-col items-center">
            <h1 className="text-[#8DECB4] font-bold text-3xl mt-44">Sign In</h1>
            {/* <input type="email" placeholder="Email" required className="outline-none text-xl w-4/12 mt-20 text-center bg-transparent border-[#8DECB4] border-b-2 text-[#8DECB4] placeholder:text-white placeholder:opacity-60" value={email} onChange={(e)=>{set_email(e.target.value)}}/>
            <input type="password" placeholder="Password" required className="outline-none text-xl w-4/12 mt-12 text-center bg-transparent border-[#8DECB4] border-b-2 text-[#8DECB4] placeholder:text-white placeholder:opacity-60" value={password} onChange={(e)=>{set_password(e.target.value)}}/>
            <button onClick={send_data} className="text-xl text-center bg-transparent border-[#8DECB4] border-2 text-white p-2 pr-4 pl-4 rounded mt-12 placeholder:text-white placeholder:opacity-60 w-4/12 hover:bg-[#8DECB4] hover:text-black transition-all ease-in-out duration-300">Sign In</button>
            <p className="mt-4 text-lg text-[#8DECB4]">or</p> */}
            <div className="flex items-center mt-4">
                <button onClick={()=>signIn("google")} className="w-[33.5vw] mt-32 flex items-center justify-center bg-[#181b2b] border-[#8DECB4] text-white border-2 rounded text-xl p-2 pr-4 pl-4 hover:bg-[#8DECB4] hover:text-black transition-all ease-in-out duration-300">
                    Continue with 
                    <img src="https://www.freepnglogos.com/uploads/google-logo-png/google-logo-icon-png-transparent-background-osteopathy-16.png" alt="google" className="w-4 ml-2"></img>
                </button>
            </div>
        </div>
        </div>
    );
};

export default SignInPage;
