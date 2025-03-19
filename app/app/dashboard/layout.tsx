"use client"
import { useState } from 'react';
import { Inter } from "next/font/google";
import "../globals.css";
import Sidebar from "../component/sidebar";

const inter = Inter({ subsets: ["latin"] });

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);

  const toggleSidebar = () => {
    setIsSidebarOpen(!isSidebarOpen);
  };

  return (
    <div className={`flex h-screen w-full bg-[#181b2b] transition-all duration-300 ease-in-out`}>
      {isSidebarOpen && (<Sidebar />)}
      <button onClick={toggleSidebar} className={`w-12 h-12 z-10 ${isSidebarOpen ? 'ml-52' : 'ml-2 mt-4 rotate-180'} transition-all duration-500 ease-in-out`}><img src="https://i.ibb.co/Bc07RZg/arrow.png" className="mt-2"></img></button>
      <div className="flex flex-col w-full h-full">
        {children}
      </div>
    </div>
  );
}