"use client"
import React, { useState } from "react";
import axios from "axios";
import { signIn, signOut, useSession } from 'next-auth/react'
import { useRouter } from 'next/navigation'

export default function Home() {
    const [link, setLink] = useState("");
    const session = useSession();
    const router = useRouter();

    const submitLink = async () => {
        if(link.trim()===""){
            return alert("URL cannot be empty")
        }
        if (session.status === "authenticated") {
            const parts = link.split("=");
            const videoId = parts[1];
            console.log(videoId);
            router.push(`/dashboard?v=${videoId}`);
        }
        if(session.status==="unauthenticated"){
            router.push("/signup")
        }
    };

    if (session.status === "loading") {
        return (
            <div className="flex justify-center mt-56">
                <img src="https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExY2N4eWw2c3F0dnRkcDJqMDNyNWdsanIxeHh4dmdudHRlZ2Z0dzB4YyZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9cw/zFwqvI1atpDkLPhBgY/giphy.gif"></img>
            </div>
        )
    }

    return (
        <div className={`min-h-screen flex flex-col bg-[#181b2b]`}>
            <header className="navbar flex justify-between sm:justify-around items-center p-4">
                <div className="flex items-center mr-4 md:mr-[40vw]">
                    <h1 className="text-xl md:text-3xl font-bold text-white">
                        Fact<span className="text-[#8DECB4]">Guard</span>
                    </h1>
                </div>
                {session.status==="unauthenticated" && (
                    <div className="flex items-center space-x-2 sm:space-x-6">
                        <button 
                            onClick={() => router.push("/signin")} 
                            className="text-white text-base md:text-xl nav-link hover:text-[#8DECB4] duration-300 transition-all ease-in-out"
                        >
                            Login
                        </button>
                        <button 
                            onClick={() => router.push("/signup")} 
                            className="text-white text-base md:text-xl nav-link hover:text-[#8DECB4] duration-300 transition-all ease-in-out"
                        >
                            Get Started
                        </button>
                    </div>
                )}
            </header>

            <main className="flex-grow flex justify-center items-center px-4">
                <div className="max-w-md w-full space-y-4 md:space-y-8">
                    <h1 className="text-2xl md:text-4xl font-bold text-center text-[#8DECB4]">
                        Video Content Factual Verification
                    </h1>
                    <p className="text-base md:text-xl text-white opacity-70 text-center">
                        Enter your YouTube video's link below to quickly start accuracy
                        assessment
                    </p>

                    <div className="flex flex-col sm:flex-row items-center gap-4">
                        <input
                            type="text"
                            className="p-2 w-full mt-4 sm:mt-8 sm:mr-4 border-[#8DECB4] border-b bg-transparent outline-none text-[#8DECB4] text-center font-mono focus:border-b-2 duration-300 transition-all ease-in-out"
                            placeholder="Enter URL of YouTube video..."
                            name="url"
                            value={link}
                            onChange={(e) => setLink(e.target.value)}
                        />
                        <button
                            onClick={submitLink}
                            className="w-full sm:w-auto bg-[#181b2b] border-[#8DECB4] border-2 text-white px-4 py-2 rounded hover:bg-[#8DECB4] hover:text-black duration-300 transition-all ease-in-out"
                        >
                            Check Facts
                        </button>
                    </div>
                </div>
            </main>
        </div>
    );
}