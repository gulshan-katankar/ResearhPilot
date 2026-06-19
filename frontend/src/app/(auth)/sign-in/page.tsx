import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import Link from "next/link";

import { login } from "@/app/(auth)/actions";

export default async function SignInPage({
  searchParams,
}: {
  searchParams: Promise<{ message: string }>;
}) {
  const params = await searchParams;
  return (
    <Card className="w-full shadow-2xl shadow-primary/10 border-border/50 bg-card/80 backdrop-blur-sm">
      <CardHeader className="space-y-2 text-center pb-8">
        <CardTitle className="text-3xl font-bold tracking-tight">Welcome back</CardTitle>
        <CardDescription className="text-base">
          Enter your email to sign in to your account
        </CardDescription>
      </CardHeader>
      <CardContent>
        {params?.message && (
          <div className="mb-4 p-3 bg-destructive/10 text-destructive text-sm rounded-md border border-destructive/20 text-center">
            {params.message}
          </div>
        )}
        <form className="space-y-6">
          <div className="space-y-2">
            <Label htmlFor="email" className="font-medium">Email</Label>
            <Input id="email" name="email" type="email" placeholder="m@example.com" required className="h-12 px-4 bg-background/50 focus:bg-background transition-colors" />
          </div>
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label htmlFor="password" className="font-medium">Password</Label>
              <Link href="#" className="text-sm font-medium text-primary hover:underline">
                Forgot password?
              </Link>
            </div>
            <Input id="password" name="password" type="password" required className="h-12 px-4 bg-background/50 focus:bg-background transition-colors" />
          </div>
          <Button formAction={login} type="submit" className="w-full h-12 text-lg rounded-xl shadow-lg shadow-primary/20">
            Sign In
          </Button>
        </form>
      </CardContent>
      <CardFooter className="flex flex-col space-y-4 text-center mt-2 pb-8">
        <div className="text-sm text-muted-foreground">
          Don&apos;t have an account?{" "}
          <Link href="/sign-up" className="font-semibold text-primary hover:underline">
            Sign up
          </Link>
        </div>
      </CardFooter>
    </Card>
  );
}
