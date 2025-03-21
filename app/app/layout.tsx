import { ReactNode } from 'react';
import Authprovider from './component/Authprovider/Authprovider';
import { Josefin_Slab } from 'next/font/google';
import './globals.css';

const josefin_slab = Josefin_Slab({
  subsets: ['latin'],
  variable: '--font-josefin-slab',
  weight: '600',
});

export const metadata = {
  title: 'FactGuard',
  description: 'Video Content Factual Accuracy Verification',
};

interface RootLayoutProps {
  children: ReactNode;
}

export default function RootLayout({ children }: RootLayoutProps) {
  return (
    <html lang="en">
      <body className={`${josefin_slab.variable}`}>
        <Authprovider>
          {children}
        </Authprovider>
      </body>
    </html>
  );
}
