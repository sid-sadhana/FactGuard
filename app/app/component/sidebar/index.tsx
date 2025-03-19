import { useState } from 'react';
import { signOut, useSession } from 'next-auth/react';
import { useRouter } from 'next/navigation'; 

const Sidebar = () => {
  const session = useSession();
  const router = useRouter();

  if(session.status==="unauthenticated"){
    router.push("/")
    return null; 
  }

  if(session.status === "loading") {
    return <div>Loading...</div>;
  }

  if(session.status === "authenticated" && session.data && session.data.user) {
    return (
      <div className="top-0 left-0 fixed h-full w-64 bg-[#181b2b] flex flex-col border-[#8DECB4] rounded-r-xl border-2">
        <div className="flex items-center flex-col">
              <h1 className="text-3xl font-bold text-white mt-2">
                Fact<span className="text-[#8DECB4]">Guard</span>
              </h1>
              {session.data.user.image && 
                <img src={session.data.user.image} className="rounded-full mt-16 border-[#8DECB4] border-2" alt="User Image" />
              }
              {session.data.user.name && 
                <h2 className="text-white mt-3 text-lg">Hello, {session.data.user.name}!</h2>
              }

        <button className="text-[#8DECB4] mt-72" onClick={async()=>{await signOut();router.push("/")}}><img className="rounded-full bg-red-400 p-2 w-12 transition-all duration-1000 ease-in-out" src="https://i.ibb.co/ZXQJ9FX/logout.png" alt="Logout"></img></button>
      </div>
      </div>
    );
  }

  return <div>Loading...</div>;
};

export default Sidebar;
