# CICD-EKS-Fargate
Designed and implemented a scalable cloud infrastructure on AWS using CodeCommit, CodeBuild, CodePipeline and ECR for CI/CD, orchestrated containerized workloads with EKS Fargate, and managed network traffic with a VPC and ALB.

## Prerequisites
- AWS CLI installed and configured
- kubectl installed
- eksctl installed
- Helm installed

## Configure Placeholders
- In below commands change resources names, regions and others as per your usecase.
- Setup for CodeCommit, CodeBuild, CodePipeline, ECR and IAM Policies are not covered here.
- Attached Final Images for above in IAM_Pics_Roles.
- Add Credentials in AWS Systems Manager parameter store (/myapp/aws-account-id, /myapp/docker-credentials/username, /myapp/docker-credentials/password).
- Configure your ECR repo name in buildspec.yaml ($AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com)
- Setting Context: Change region and cluster name in buildspec.yaml (aws eks --region us-east-1 update-kubeconfig --name cicd-cluster).
#### Check buildspec.yml for initial execution many fields are commented to achieve the primary target of pushing image to ECR.
#### Once Image is in ECR and EKS Cluster is created with service and ingress, Will follow regular CICD Flow whenever changes are committed.

## 1. Create EKS Cluster
- To create an EKS cluster named `cicd-cluster` in the `us-east-1` region with Fargate, use the following command:
```
eksctl create cluster --name cicd-cluster --region us-east-1 --fargate
```

## 2. Update kubeconfig in terminal
```
aws eks update-kubeconfig --name cicd-cluster --region us-east-1
```

#### error fix in between: error: You must be logged in to the server (Unauthorized)
- link: https://docs.aws.amazon.com/eks/latest/userguide/add-user-role.html
```
kubectl create clusterrolebinding codebuild-simple-python-flask-servic-service-role-cluster-admin-binding --clusterrole=cluster-admin --user=codebuild-simple-python-flask-servic-service-role
```

#### while copying IAM arn no service-role in between arn:aws:eks:us-east-1:<ACCOUNT_ID>:cluster/cicd-cluster
- link: https://blog.searce.com/aws-pipeline-to-create-ecr-image-ci-and-deploy-cd-nodejs-application-on-eks-a9550add782c
```
eksctl create iamidentitymapping --cluster cicd-cluster --arn arn:aws:iam::<ACCOUNT_ID>:role/codebuild-simple-python-flask-servic-service-role --group system:masters --username codebuild-simple-python-flask-servic-service-role
```
#### Skipping fargate profile creation step i am going with default profile.

## 3. Apply service.yaml and ingress.yaml (One time activity, deployment will be triggered next time from buildspec.yml)
```
kubectl apply -f kubernetes/deployment.yaml
kubectl apply -f kubernetes/service.yaml
# will use ingress to route the traffic inside the cluster
kubectl apply -f kubernetes/ingress.yaml
```

#### Check for service external IP it will be blank.
```
kubectl get svc
```
- Access only within the VPC.
- To access outside of VPC we need external ip.
- Also describe and check for events if there are any issues.
#### Check Ingress
```
kubectl get ingress
```
- Address will be empty as there is no ingress controller.
- Also describe and check for events if there are any issues.

## 4. OpenID Setup
- This setup enables the integration between AWS IAM (Identity and Access Management) and Kubernetes service accounts, offering a more secure and efficient way to manage access to AWS resources from within your Kubernetes pods.
- Kubernetes and AWS are separate systems with their own authentication and authorization mechanisms. Here's why the association of an IAM OIDC (OpenID Connect) provider is crucial
- The IAM OIDC provider creates a trust relationship between AWS IAM and the Kubernetes service accounts
- OIDC identity provider is linked to your EKS cluster and serves as a bridge between the Kubernetes service accounts in your cluster and AWS IAM.
- Enables IAM Roles for Service Accounts (IRSA): With the OIDC provider associated with your EKS cluster, you can now use IRSA. This feature allows you to assign specific IAM roles to Kubernetes service accounts.
```
eksctl utils associate-iam-oidc-provider --cluster cicd-cluster --approve
```

## 5. Create IAM Policy For ALB Controller to access AWS resources
```
command 1: curl -O https://raw.githubusercontent.com/kubernetes-sigs/aws-load-balancer-controller/v2.5.4/docs/install/iam_policy.json
command 2: aws iam create-policy \
    --policy-name AWSLoadBalancerControllerIAMPolicy \
    --policy-document file://iam_policy.json
```
## 6. Create IAM Service account; attaching above created role to this account
```
eksctl create iamserviceaccount \
  --cluster=cicd-cluster \
  --namespace=kube-system \
  --name=aws-load-balancer-controller \
  --role-name AmazonEKSLoadBalancerControllerRole \
  --attach-policy-arn=arn:aws:iam::<ACCOUNTID>:policy/AWSLoadBalancerControllerIAMPolicy \
  --approve
```

## 7. ALB Controller Installation
- Loadbalancer acts as ingress controller.
- ALB is present in public subnet(As its all in the same vpc it can access pods in private subnet).
- When the ingress controller finds ingress object it will create and configure application loadbalancer.
```
command 1: helm repo add eks https://aws.github.io/eks-charts
command 2: helm repo update eks
command 3: helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
  -n kube-system \
  --set clusterName=<** cicd-cluster **> \
  --set serviceAccount.create=false \
  --set serviceAccount.name=aws-load-balancer-controller \
  --set region=<** us-east-1 **> \
  --set vpcId=< **vpc-02 **>
```

- Now check if address is present; ingress resource has ingress controller
- Logs Check: kubectl logs -n kube-system -l app.kubernetes.io/name=aws-load-balancer-controller
- LoadBalancer will be created in AWS Console check in ec2/Loadbalancers
- If you dont find loadbalancer in UI there might be some issue with ingress creation; recheck ingress events.
## 8. Verify:
```
kubectl get deployments -n kube-system
```
## 9. Some Helper Commands:
- List and delete a helm release
```
command 1: helm list -n kube-system
command 2: helm delete aws-load-balancer-controller -n kube-system
```



